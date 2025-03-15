from .engine import db_url
def handler(event, context):
    print(db_url)
    return {"statusCode": 200, "message" : "Watchlist Sent"}