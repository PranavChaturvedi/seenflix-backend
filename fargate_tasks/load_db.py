from models.sa_models import UserWatchLog, SeenFlixAggregated, TVEpisodeCount
import boto3
from dotenv import load_dotenv

load_dotenv('.env')


# Getting Supbase and TMDB Variables from SSM 

ssm_client = boto3.client("ssm")

# SUPBASE_VALUES

supabase_db_result = ssm_client.get_parameters_by_path(
    Path="/supabase/",
    Recursive=True,
)
tmdb_result = ssm_client.get_parameters_by_path(
    Path="/tmdb/",
    Recursive=True,
)
supabase_db_params = dict()
for param in supabase_db_result.get("Parameters",[]):
    supabase_db_params[param["ARN"].split('/')[-1]] = param['Value']

# Getting backup csv files from S3

# Getting movie and TV Show DF


# Loop through Movies and Add inside SeenFlix aggregated (insert on conflict do upadate)

# Loop through Shows DF and add inside SeenFlixAggregated and Episode Count