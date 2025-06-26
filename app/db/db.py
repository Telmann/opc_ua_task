import os

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()
DATABASE_URL = os.getenv("DB_URL")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DB_URL")

engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)
sync_engine = create_engine(DATABASE_URL)

metadata = MetaData()
Base = declarative_base()
