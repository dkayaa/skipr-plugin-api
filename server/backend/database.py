import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

Base = declarative_base()

_engine = None
db_session = None


def build_database_url() -> str:
    user = os.getenv("DB_USER", "user")
    password = os.getenv("DB_PASSWORD", "password")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "skipr_db")
    return f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{name}"


def get_engine():
    global _engine, db_session
    if _engine is None:
        _engine = create_engine(build_database_url(), pool_pre_ping=True)
        db_session = scoped_session(sessionmaker(
            bind=_engine, autocommit=False, autoflush=False))
    return _engine


def get_session():
    get_engine()
    return db_session()


def init_app(app):
    get_engine()

    @app.teardown_appcontext
    def shutdown_session(_exception=None):
        if db_session is not None:
            db_session.remove()
