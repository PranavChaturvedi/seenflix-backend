from .engine import connection
from models.sa_models import SeenFlixAggregated
from sqlalchemy import select, func
import json
from .common import DateJSONEncode


def handler(event, context):
    query_params = event.get("queryStringParameters", {})
    if "title" not in query_params.keys():
        raise ValueError("No Title filter for Searching")
    title = query_params["title"]
    title = str(title).upper()

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
        .where(func.upper(SeenFlixAggregated.c.title).like(f"{title}%"))
        .order_by(SeenFlixAggregated.c.release_date.desc())
        .limit(8)
    )

    data = connection.execute(query).mappings().all()
    connection.commit()
    data = [dict(mapping) for mapping in data]
    return {"statusCode": 200, "body": json.dumps(data, cls=DateJSONEncode)}
