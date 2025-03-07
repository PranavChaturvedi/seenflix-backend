from models.sa_models import SeenFlixAggregated, metadata
import boto3
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql as pg
import requests
import gzip
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
from io import BytesIO
import time

load_dotenv(".env")


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
            response = session.get(api_url, timeout=10)
            if response.status_code != 200:
                return {"tmdb_id": tmdb_id, "status": "failed", "error": "HTTP error"}

            movie_detail = response.json()
            if not movie_detail.get("imdb_id"):
                return {"tmdb_id": tmdb_id, "status": "skipped", "error": "No IMDb ID"}

            entry = {
                "type": media_type,
                "backdrop_path": movie_detail["backdrop_path"],
                "poster_path": movie_detail["poster_path"],
                "original_language": movie_detail["original_language"],
                "release_date": movie_detail["release_date"],
                "imdb_id": movie_detail["imdb_id"],
                "title": movie_detail["title"],
                "homepage": movie_detail["homepage"],
                "overview": movie_detail["overview"],
                "status": movie_detail["status"],
                "tagline": movie_detail["tagline"],
                "genre": [i["name"] for i in movie_detail["genres"]],
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

# Movies addition

tmdb_ids = []
two_days_ago_datetime = datetime.datetime.today() - datetime.timedelta(days=2)
two_days_ago_datetime = two_days_ago_datetime.date().strftime("%m_%d_%Y")

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
with ThreadPoolExecutor(max_workers=30) as executor:
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
print("Processing completed. Results:")
for result in results:
    if result["status"] not in result_dict.keys():
        result_dict[result["status"]] = 0
    else:
        result_dict[result["status"]] += 1
print(result_dict)

# TV Series Addition
