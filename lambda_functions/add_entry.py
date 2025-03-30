from .engine import connection
from models.sa_models import UserWatchLog
from sqlalchemy.dialects import postgresql as pg
import json


def handler(event, context):
    user_id = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
        .get("id", None)
    )
    payload = json.loads(event.get("body", "{}"))
    if payload.get("imdb_id", None) is None:
        return {"statusCode": 400, "body": "Cannot add this Media"}
    entry = {**payload, "user_id": user_id}
    UserWatchLog.create(bind=connection, checkfirst=True)
    insert_query = (
        pg.insert(UserWatchLog)
        .values(entry)
        .on_conflict_do_update(set_=entry, constraint="media_uniqueness")
    )
    connection.execute(insert_query)
    connection.commit()
    return {"statusCode": 200, "body": "Media Added"}
