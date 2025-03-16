from .engine import connection
from sqlalchemy import select
import json
from .common import DateJSONEncode
from models.sa_models import SeenFlixAggregated, UserWatchLog


def handler(event, context):
    user_id = event.get("user_id")
    query = (
        select(
            SeenFlixAggregated.c.imdb_id,
            SeenFlixAggregated.c.type,
            SeenFlixAggregated.c.homepage,
            SeenFlixAggregated.c.poster_path,
            SeenFlixAggregated.c.backdrop_path,
            SeenFlixAggregated.c.title,
            SeenFlixAggregated.c.tagline,
            SeenFlixAggregated.c.overview,
            SeenFlixAggregated.c.status,
            SeenFlixAggregated.c.genre,
            SeenFlixAggregated.c.release_date,
            SeenFlixAggregated.c.original_language,
        )
        .select_from(
            SeenFlixAggregated.join(
                UserWatchLog, UserWatchLog.c.imdb_id == SeenFlixAggregated.c.imdb_id
            )
        )
        .where(UserWatchLog.c.user_id == user_id)
    )
    data = connection.execute(query).mappings().all()
    data = [dict(mapping) for mapping in data]
    return {"statusCode": 200, "body": json.dumps(data, cls=DateJSONEncode)}
