from sqlalchemy.dialects.postgresql import INTEGER, VARCHAR, TEXT, DATE, ARRAY, ENUM
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UserWatchLog(Base):
    __tablename__ = "user_watchlog"
    user_id = VARCHAR(255, primary_key=True)
    imdb_id = VARCHAR(50, nullable=False)
    rating = INTEGER(nullable=False)
    comment = TEXT()
    status = ENUM("left","watching","completed",name="status_enum")
    watched_till = VARCHAR(20, nullable=False)

