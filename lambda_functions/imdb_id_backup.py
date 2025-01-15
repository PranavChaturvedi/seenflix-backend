import pandas as pd
import constants
import boto3
import http



def handler(event, context):
    s3_client = boto3.client("s3")
    status_object = {}
    try:
        df_films = pd.read_csv(constants.FILMS_LINK)
        s3_client.put_object(
            Bucket=constants.BACKUP_UPLOAD_BUCKET,
            Key="films_backup.csv",
            Body=df_films
        )

        df_series = pd.read_csv(constants.SERIES_LINK)
        s3_client.put_object(
            Bucket=constants.BACKUP_UPLOAD_BUCKET,
            Key="series_backup.csv",
            Body=df_series
        )

        status_object["statusCode"] =  http.HTTPStatus.OK
        status_object["message"] = "CRON Job Completed Successfully"
    except Exception as e:
        print(e)
        status_object["statusCode"] = http.HTTPStatus.INTERNAL_SERVER_ERROR
        status_object["message"] = "Upload to s3 failed"
    finally:
        # Try to add a function to send mails with the outcome of the cron job
        pass
    return status_object