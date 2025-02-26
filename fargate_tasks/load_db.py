from models.sa_models import SeenFlixAggregated, TVEpisodeCount, metadata
import boto3
from dotenv import load_dotenv
from sqlalchemy import create_engine, insert
import pandas as pd
import requests

load_dotenv(".env")


# Getting Supbase and TMDB Variables from SSM

ssm_client = boto3.client("ssm")
s3_client = boto3.client("s3")
films_backup_file = "films_backup.csv"
series_backup_file = "series_backup.csv"

supabase_db_result = ssm_client.get_parameters_by_path(
    Path="/supabase/",
    Recursive=True,
)
tmdb_result = ssm_client.get_parameters_by_path(
    Path="/tmdb/",
    Recursive=True,
    WithDecryption=True
)
s3_backup_bucket = (
    ssm_client.get_parameter(Name="/imdb/backup/bucket")
    .get("Parameter", {})
    .get("Value", None)
)
supabase_db_params = dict()
tmdb_api_params = dict()
for param in supabase_db_result.get("Parameters", []):
    supabase_db_params[param["ARN"].split("/")[-1]] = param["Value"]
for param in tmdb_result.get("Parameters"):
    tmdb_api_params[param["ARN"].split("/")[-1]] = param["Value"]

# Getting backup csv files from S3

if s3_backup_bucket:
    s3_client.download_file(s3_backup_bucket, films_backup_file, films_backup_file)
    s3_client.download_file(s3_backup_bucket, series_backup_file, series_backup_file)

# Getting movie and TV Show DF

films_df = pd.read_csv(films_backup_file)
series_df = pd.read_csv(series_backup_file)

# Creating engine

connection_string = f"postgresql+psycopg2://{supabase_db_params['user']}:{supabase_db_params['password']}@{supabase_db_params['host']}:{supabase_db_params['port']}/postgres"

supabase_engine = create_engine(connection_string)

# Create tables if not created already

with supabase_engine.begin() as connection:
    metadata.create_all(bind=connection,checkfirst=True)
    
    films_imdb_ids = films_df['IMDB_ID'].tolist()
    for imdb_id in films_imdb_ids:
        api_url = f"https://{tmdb_api_params['path']}/3/find/{imdb_id}?api_key={tmdb_api_params['key']}&external_source=imdb_id"
        response = requests.get(api_url).json()
        movie_detail = response["movie_results"][0]
        id = movie_detail["id"]
        entry = {
            "type": "movie",
            "backdrop_path": movie_detail["backdrop_path"],
            "poster_path": movie_detail["poster_path"],
            "original_language": movie_detail["original_language"],
            "release_date": movie_detail["release_date"],
            "imdb_id" : imdb_id,
            "title" : movie_detail["title"],
            "overview": movie_detail["overview"],
        }      

        misc_query_url = f"https://{tmdb_api_params['path']}/3/movie/{id}?api_key={tmdb_api_params['key']}"
        misc_response = requests.get(misc_query_url).json()
        entry["tagline"] = misc_response["tagline"]
        entry["homepage"] = misc_response["homepage"]
        entry["status"] = misc_response["status"]
        entry["genre"] = [i["name"] for i in misc_response["genres"]]

        # make it insert into update
        connection.execute(insert(SeenFlixAggregated).values(entry))        

# Loop through Movies and Add inside SeenFlix aggregated (insert on conflict do upadate)

# Loop through Shows DF and add inside SeenFlixAggregated and Episode Count
