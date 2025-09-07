import os
from databases import Database
from sqlalchemy import create_engine
from models import mapper_registry

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:3554@localhost/testdatabase")

database = Database(DATABASE_URL)
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(SYNC_DATABASE_URL)
metadata = mapper_registry.metadata
