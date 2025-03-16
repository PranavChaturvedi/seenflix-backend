import sqlalchemy
import os

db_url = sqlalchemy.URL(
    drivername="postgresql+psycopg2",
    username=os.environ["SUPABASE_USER"],
    database="postgres",
    password=os.environ["SUPABASE_PASSWORD"],
    host=os.environ["SUPABASE_HOST"],
    port=os.environ["SUPABASE_PORT"],
    query={},
)

engine = sqlalchemy.create_engine(
    url=db_url, pool_size=10, max_overflow=5, pool_pre_ping=True, pool_recycle=900
)
connection = engine.connect()
