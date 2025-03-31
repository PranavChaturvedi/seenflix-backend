from .engine import connection
from sqlalchemy import select, func, case
import json
from .common import DateJSONEncode
from models.sa_models import SeenFlixAggregated, UserWatchLog


def handler(event, context):
    # returning random data right now
    user_id = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
        .get("id", None)
    )
    if user_id is None:
        return {"statusCode": 400, "body": "User ID not found"}
    query = (
        select(
            *SeenFlixAggregated.c,
            case((UserWatchLog.c.user_id == user_id, "added"), else_="not_added").label(
                "user_status"
            ),
        )
        .select_from(
            SeenFlixAggregated.outerjoin(
                UserWatchLog, UserWatchLog.c.imdb_id == SeenFlixAggregated.c.imdb_id
            )
        )
        .order_by(func.random())
        .limit(15)
    )
    data = connection.execute(query).mappings().all()
    data = [dict(mapping) for mapping in data]
    return {"statusCode": 200, "body": json.dumps(data, cls=DateJSONEncode)}
