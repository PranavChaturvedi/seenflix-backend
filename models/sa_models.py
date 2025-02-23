from sqlalchemy.dialects.postgresql import INTEGER, VARCHAR, TEXT, DATE, ARRAY, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, MetaData, Column, ForeignKeyConstraint

Base = declarative_base()

metadata = MetaData(schema="public")

SeenFlixAggregated = Table(
    "seenflix_aggregated",
    metadata,
    Column("auto_id", INTEGER, primary_key=True, autoincrement="auto"),
    Column("imdb_id",VARCHAR(100),unique=True),
    Column("type",ENUM("movie","tv_show",name="media_type")),
    Column("homepage",VARCHAR(255)),
    Column("poster_path",VARCHAR(100)),
    Column("backdrop_path",VARCHAR(100)),
    Column("title",TEXT),
    Column("tagline",TEXT),
    Column("overview",TEXT),
    Column("status",TEXT),
    Column("release_date",DATE),
    Column("original_language",VARCHAR(10)),
    comment="Aggregated List for all avaiable Movies and Shows"
)

UserWatchLog = Table(
    "user_watchlog",
    metadata,
    Column("user_id",VARCHAR(255), primary_key=True),
    Column("imdb_id",VARCHAR(100),nullable=False),
    Column("rating",INTEGER, nullable=False),
    Column("comment", TEXT),
    Column("status",ENUM("left","watching","completed","planned",name="status_enum")),
    Column("watched_till", VARCHAR(20)),
    ForeignKeyConstraint(["imdb_id"],["seenflix_aggregated.imdb_id"],name="imdb_fk_logs"),
    comment="Table for storing user watchlogs",
)

TVEpisodeCount = Table(
    "tv_season_episode_count",
    metadata,
    Column("auto_id",INTEGER,primary_key=True, autoincrement="auto"),
    Column("imdb_id",VARCHAR(100),nullable=False),
    Column("season",INTEGER),
    Column("episode",INTEGER),
    ForeignKeyConstraint(["imdb_id"],["seenflix_aggregated.imdb_id"],name="imdb_fk_ep_count"),
    comment="TV Show Episode Count"
)

