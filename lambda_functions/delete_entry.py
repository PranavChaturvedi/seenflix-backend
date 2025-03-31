from .engine import connection
from models.sa_models import UserWatchLog
from sqlalchemy import delete, and_

def handler(event, context):
    user_id = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
        .get("id", None)
    )
    if user_id is None:
        return {"statusCode": 400, "body": "User ID not found"}
    params = event.get("queryStringParameters")
    if params.get("imdb_id", None) is None:
        return {"statusCode": 400, "body": "Cannot delete this Media"}
    delete_query = (
        delete(UserWatchLog).where(and_(UserWatchLog.c.user_id == user_id, UserWatchLog.c.imdb_id == params.get("imdb_id")))
    )
    connection.execute(delete_query)
    connection.commit()
    return {"statusCode": 200, "body": "Media Deleted"}
