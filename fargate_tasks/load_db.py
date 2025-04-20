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

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--media", help="Select Media Type to Load")


# Getting Supbase and TMDB Variables from SSM

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

# Create tables if not created already

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


with supabase_engine.begin() as connection:
    print("Connection has been established to Supabase")
    metadata.create_all(bind=connection, checkfirst=True)


two_days_ago_datetime = datetime.datetime.today() - datetime.timedelta(days=2)
two_days_ago_datetime = two_days_ago_datetime.date().strftime("%m_%d_%Y")

args = parser.parse_args()

if args.media in ["both", "movie"]:
    # Movies addition

    print("Movie Addition Begins")

    movie_file_name = f"movie_ids_{two_days_ago_datetime}.json.gz"
    download_movie_gzip_url = f"http://files.tmdb.org/p/exports/{movie_file_name}"
    response = requests.get(download_movie_gzip_url, allow_redirects=True)

    movie_tmdb_objects = []
    with gzip.GzipFile(fileobj=BytesIO(response.content)) as gz:
        for line in gz:
            movie_tmdb_objects.append(json.loads(line.decode()))
        movie_tmdb_ids = [obj["id"] for obj in movie_tmdb_objects]
    print(f"Adding Data for {len(movie_tmdb_ids)} films.")

    worker_inputs = list(zip(movie_tmdb_ids, ["movie"] * len(movie_tmdb_ids)))

    results = []
    result_dict = {}
    error_dict = {}
    with ThreadPoolExecutor(max_workers=25) as executor:
        # Submit tasks to the executor
        futures = [
            executor.submit(add_media_into_supbase, tmdb_id, media_type)
            for tmdb_id, media_type in worker_inputs
        ]

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({"status": "failed", "error": str(e)})

    # Print or process results after all threads are done
    print("Movies Processing completed. Results:")
    for result in results:
        if result["status"] not in result_dict.keys():
            result_dict[result["status"]] = 1
        else:
            result_dict[result["status"]] += 1
        if result["status"] == "failed":
            if result["error"] not in error_dict.keys():
                error_dict[result["error"]] = 1
            else:
                error_dict[result["error"]] += 1
    print(result_dict)
    print(error_dict)

# TV Series Addition

if args.media in ["both", "tv"]:
    print("TV Addition Begins")

    tv_series_file_name = f"tv_series_ids_{two_days_ago_datetime}.json.gz"
    download_tv_gzip_url = f"http://files.tmdb.org/p/exports/{tv_series_file_name}"
    tv_response = requests.get(download_tv_gzip_url, allow_redirects=True)

    tv_series_objects = []
    with gzip.GzipFile(fileobj=BytesIO(tv_response.content)) as gz:
        for line in gz:
            tv_series_objects.append(json.loads(line.decode()))
        tv_tmdb_ids = [obj["id"] for obj in tv_series_objects]

    print(f"Adding Data for {len(tv_tmdb_ids)} TV Series.")

    worker_inputs = list(zip(tv_tmdb_ids, ["tv"] * len(tv_tmdb_ids)))

    results = []
    result_dict = {}
    error_dict = {}
    with ThreadPoolExecutor(max_workers=25) as executor:
        # Submit tasks to the executor
        futures = [
            executor.submit(add_media_into_supbase, tmdb_id, media_type)
            for tmdb_id, media_type in worker_inputs
        ]

        # Collect results as they complete
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({"status": "failed", "error": str(e)})

    # Print or process results after all threads are done
    print("TV Show Processing completed. Results:")
    for result in results:
        if result["status"] not in result_dict.keys():
            result_dict[result["status"]] = 1
        else:
            result_dict[result["status"]] += 1
        if result["status"] == "failed":
            if result["error"] not in error_dict.keys():
                error_dict[result["error"]] = 1
            else:
                error_dict[result["error"]] += 1
    print(result_dict)
    print(error_dict)
