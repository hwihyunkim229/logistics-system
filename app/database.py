from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL.startswith("postgresql"):

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={
            "options": "-c timezone=Asia/Seoul"
        }
    )

else:

    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False
        }
    )

SessionLocal = sessionmaker(
    bind=engine
)

Base = declarative_base()