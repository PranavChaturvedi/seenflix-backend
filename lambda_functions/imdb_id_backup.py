import pandas as pd
from . import constants
import boto3
import http
import os
import io

def handler(event, context):
    s3_client = boto3.client("s3")
    status_object = {}
    backup_s3_bucket = os.environ.get("IMDB_IDS_BACKUP_BUCKET")
    
    try:
        # Read the dataframes from the constants
        df_films = pd.read_csv(constants.FILMS_LINK)
        df_series = pd.read_csv(constants.SERIES_LINK)
        
        # Define the keys for the S3 objects
        films_key = "films_backup.csv"
        series_key = "series_backup.csv"
        
        # Check if the files already exist in the S3 bucket
        films_exists = False
        series_exists = False
        
        objects_list = s3_client.list_objects_v2(Bucket=backup_s3_bucket)
        if 'Contents' in objects_list:
            for obj in objects_list['Contents']:
                if obj['Key'] == films_key:
                    films_exists = True
                if obj['Key'] == series_key:
                    series_exists = True
        
        # If the files exist, delete them
        if films_exists:
            s3_client.delete_object(Bucket=backup_s3_bucket, Key=films_key)
        if series_exists:
            s3_client.delete_object(Bucket=backup_s3_bucket, Key=series_key)
        
        # Convert dataframes to CSV and upload to S3
        films_csv_buffer = io.StringIO()
        df_films.to_csv(films_csv_buffer, index=False)
        s3_client.put_object(
            Bucket=backup_s3_bucket,
            Key=films_key,
            Body=films_csv_buffer.getvalue()
        )
        
        series_csv_buffer = io.StringIO()
        df_series.to_csv(series_csv_buffer, index=False)
        s3_client.put_object(
            Bucket=backup_s3_bucket,
            Key=series_key,
            Body=series_csv_buffer.getvalue()
        )
        
        status_object["statusCode"] = http.HTTPStatus.OK
        status_object["message"] = "CRON Job Completed Successfully"
    
    except Exception as e:
        print(e)
        status_object["statusCode"] = http.HTTPStatus.INTERNAL_SERVER_ERROR
        status_object["message"] = "Upload to S3 failed"
    
    finally:
        # Try to add a function to send mails with the outcome of the cron job
        pass
    
    return status_object