from models.sa_models import UserWatchLog, SeenFlixAggregated, TVEpisodeCount
import boto3
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd

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

# supabase_engine = create_engine(f"postgresql+psycopg2://{supabase_db_params['user']}:{supabase_db_params['password']}@{supabase_db_params['host']}:{supabase_db_params['port']}/database")

# Create tables if not created already

# Loop through Movies and Add inside SeenFlix aggregated (insert on conflict do upadate)

# Loop through Shows DF and add inside SeenFlixAggregated and Episode Count
