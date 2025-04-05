from .engine import connection
from sqlalchemy import select, func, case, and_
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
    query = (
        select(
            *SeenFlixAggregated.c,
            case((and_(UserWatchLog.c.user_id == user_id,UserWatchLog.c.user_id.isnot(None)), "added"), else_="not_added").label(
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
