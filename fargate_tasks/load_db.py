from models.sa_models import SeenFlixAggregated, metadata
import boto3
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql as pg
import requests
import gzip
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
from io import BytesIO
import time
import argparse
from collections import defaultdict
import gc

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--media", help="Select Media Type to Load")

# Getting Supabase and TMDB Variables from SSM
ssm_client = boto3.client("ssm")

supabase_db_result = ssm_client.get_parameters_by_path(
    Path="/supabase/",
    Recursive=True,
)
tmdb_result = ssm_client.get_parameters_by_path(
    Path="/tmdb/", Recursive=True, WithDecryption=True
)
supabase_db_params = dict()
tmdb_api_params = dict()
for param in supabase_db_result.get("Parameters", []):
    supabase_db_params[param["ARN"].split("/")[-1]] = param["Value"]
for param in tmdb_result.get("Parameters"):
    tmdb_api_params[param["ARN"].split("/")[-1]] = param["Value"]

# Creating engine
connection_string = f"postgresql+psycopg2://{supabase_db_params['user']}:{supabase_db_params['password']}@{supabase_db_params['host']}:{supabase_db_params['port']}/postgres"
supabase_engine = create_engine(connection_string, pool_size=35, max_overflow=32)

session = requests.Session()


def add_media_into_supbase(tmdb_id, media_type):
    try:
        with supabase_engine.begin() as connection:
            api_url = f"https://{tmdb_api_params['path']}/3/{media_type}/{tmdb_id}?api_key={tmdb_api_params['key']}"
            if media_type == "tv":
                api_url += "&append_to_response=external_ids"
            response = session.get(api_url, timeout=10)
            if response.status_code != 200:
                return {
                    "tmdb_id": tmdb_id,
                    "status": "failed",
                    "error": f"HTTP error : {response.status_code}",
                }

            media_detail = response.json()
            if not media_detail.get("imdb_id") and not media_detail.get(
                "external_ids", {}
            ).get("imdb_id"):
                return {"tmdb_id": tmdb_id, "status": "skipped", "error": "No IMDb ID"}
            elif (
                media_detail.get("imdb_id")
                or media_detail.get("external_ids", {}).get("imdb_id")
            ) == "tt0137523":
                return {
                    "tmdb_id": tmdb_id,
                    "status": "skipped",
                    "error": "Special Case : Fight Club",
                }

            entry = {
                "type": media_type,
                "backdrop_path": media_detail["backdrop_path"],
                "poster_path": media_detail["poster_path"],
                "original_language": media_detail["original_language"],
                "release_date": media_detail.get(
                    "release_date", media_detail.get("first_air_date")
                )
                or None,
                "imdb_id": media_detail.get(
                    "imdb_id", media_detail.get("external_ids", {}).get("imdb_id")
                ),
                "title": media_detail.get("title", media_detail.get("name")),
                "homepage": media_detail["homepage"],
                "overview": media_detail["overview"],
                "status": media_detail["status"],
                "tagline": media_detail["tagline"],
                "genre": [i["name"] for i in media_detail["genres"]],
            }

            connection.execute(
                pg.insert(SeenFlixAggregated)
                .values(entry)
                .on_conflict_do_update(
                    index_elements=[SeenFlixAggregated.c.imdb_id], set_=entry
                )
            )
            time.sleep(1)  # Rate limiting
            return {"tmdb_id": tmdb_id, "status": "success"}

    except Exception as e:
        return {"tmdb_id": tmdb_id, "status": "failed", "error": str(e)}


def stream_process_gzip_ids(url, media_type, batch_size=100, max_workers=10):
    """Stream process IDs from gzip file in batches to avoid memory issues"""
    
    print(f"Starting {media_type} processing with batch_size={batch_size}, max_workers={max_workers}")
    
    response = requests.get(url, stream=True)  # Stream the response
    if response.status_code != 200:
        raise Exception(f"Failed to download {url}: {response.status_code}")
    
    # Overall statistics
    overall_stats = defaultdict(int)
    overall_errors = defaultdict(int)
    total_processed = 0
    
    batch_ids = []
    
    # Process the gzip file line by line
    with gzip.GzipFile(fileobj=BytesIO(response.content)) as gz:
        for line in gz:
            try:
                obj = json.loads(line.decode())
                batch_ids.append(obj["id"])
                
                # Process batch when it reaches batch_size
                if len(batch_ids) >= batch_size:
                    stats, errors, processed = process_batch(batch_ids, media_type, max_workers)
                    
                    # Update overall statistics
                    for status, count in stats.items():
                        overall_stats[status] += count
                    for error, count in errors.items():
                        overall_errors[error] += count
                    
                    total_processed += processed
                    print(f"Processed batch of {processed} items. Total so far: {total_processed}")
                    print(f"Batch stats: {dict(stats)}")
                    
                    # Clear batch and force garbage collection
                    batch_ids = []
                    gc.collect()
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON line: {e}")
                continue
    
    # Process remaining items in the last batch
    if batch_ids:
        stats, errors, processed = process_batch(batch_ids, media_type, max_workers)
        for status, count in stats.items():
            overall_stats[status] += count
        for error, count in errors.items():
            overall_errors[error] += count
        total_processed += processed
        print(f"Processed final batch of {processed} items.")
    
    print(f"\n{media_type.upper()} Processing completed!")
    print(f"Total processed: {total_processed}")
    print(f"Overall stats: {dict(overall_stats)}")
    if overall_errors:
        print(f"Overall errors: {dict(overall_errors)}")
    
    return overall_stats, overall_errors


def process_batch(tmdb_ids, media_type, max_workers):
    """Process a batch of TMDB IDs"""
    batch_stats = defaultdict(int)
    batch_errors = defaultdict(int)
    
    worker_inputs = [(tmdb_id, media_type) for tmdb_id in tmdb_ids]
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit only this batch to the executor
        futures = [
            executor.submit(add_media_into_supbase, tmdb_id, media_type)
            for tmdb_id, media_type in worker_inputs
        ]
        
        # Process results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                batch_stats[result["status"]] += 1
                
                if result["status"] == "failed":
                    batch_errors[result.get("error", "Unknown error")] += 1
                    
            except Exception as e:
                batch_stats["failed"] += 1
                batch_errors[str(e)] += 1
    
    return batch_stats, batch_errors, len(tmdb_ids)


# Initialize database
with supabase_engine.begin() as connection:
    print("Connection has been established to Supabase")
    metadata.create_all(bind=connection, checkfirst=True)

two_days_ago_datetime = datetime.datetime.today() - datetime.timedelta(days=2)
two_days_ago_datetime = two_days_ago_datetime.date().strftime("%m_%d_%Y")

args = parser.parse_args()

# Configuration - adjust these based on your ECS memory allocation
BATCH_SIZE = 50  # Process 50 items at a time
MAX_WORKERS = 8  # Reduce concurrent threads

if args.media in ["both", "movie"]:
    print("Movie Addition Begins")
    movie_file_name = f"movie_ids_{two_days_ago_datetime}.json.gz"
    download_movie_gzip_url = f"http://files.tmdb.org/p/exports/{movie_file_name}"
    
    stream_process_gzip_ids(download_movie_gzip_url, "movie", BATCH_SIZE, MAX_WORKERS)

if args.media in ["both", "tv"]:
    print("TV Addition Begins")
    tv_series_file_name = f"tv_series_ids_{two_days_ago_datetime}.json.gz"
    download_tv_gzip_url = f"http://files.tmdb.org/p/exports/{tv_series_file_name}"
    
    stream_process_gzip_ids(download_tv_gzip_url, "tv", BATCH_SIZE, MAX_WORKERS)
