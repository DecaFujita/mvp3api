from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, inspect, text
import os

from model.base import Base
from model.provider import Provider
from model.activity import Activity
from model.session import Session
from model.provider_activity import ProviderActivity

db_path = "database/"
if not os.path.exists(db_path):
   os.makedirs(db_path)

db_url = 'sqlite:///%s/db.sqlite3' % db_path

engine = create_engine(db_url, echo=False)

SessionLocal = sessionmaker(bind=engine)

if not database_exists(engine.url):
    create_database(engine.url) 

Base.metadata.create_all(engine)

_insp = inspect(engine)
if _insp.has_table("provider"):
    _provider_cols = {c["name"] for c in _insp.get_columns("provider")}
    if "email" not in _provider_cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE provider ADD COLUMN email VARCHAR(255)"))

    _provider_sql = _insp.get_table_options("provider") if False else None
    with engine.connect() as conn:
        _definition = conn.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='provider'")
        ).scalar() or ""

    if "AUTOINCREMENT" not in _definition.upper():
        with engine.begin() as conn:
            _last_provider_id = conn.execute(text("""
                SELECT MAX(id) FROM (
                    SELECT id FROM provider
                    UNION ALL SELECT provider_id FROM session
                    UNION ALL SELECT provider_id FROM provider_activity
                )
            """)).scalar() or 0
            conn.execute(text("""
                CREATE TABLE provider_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(140) NOT NULL,
                    address VARCHAR(255), city VARCHAR(100) NOT NULL,
                    state VARCHAR(100) NOT NULL, phone VARCHAR(50),
                    instagram VARCHAR(255) NOT NULL, email VARCHAR(255),
                    description VARCHAR(500), created_at DATETIME, active BOOLEAN
                )
            """))
            conn.execute(text("""
                INSERT INTO provider_new
                    (id, name, address, city, state, phone, instagram, email, description, created_at, active)
                SELECT id, name, address, city, state, phone, instagram, email, description, created_at, active
                FROM provider
            """))
            conn.execute(text("DROP TABLE provider"))
            conn.execute(text("ALTER TABLE provider_new RENAME TO provider"))
            conn.execute(
                text("UPDATE sqlite_sequence SET seq = :seq WHERE name = 'provider'"),
                {"seq": _last_provider_id},
            )

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM session
            WHERE provider_id NOT IN (SELECT id FROM provider)
               OR activity_id NOT IN (SELECT id FROM activity)
        """))
        conn.execute(text("""
            DELETE FROM provider_activity
            WHERE provider_id NOT IN (SELECT id FROM provider)
               OR activity_id NOT IN (SELECT id FROM activity)
        """))
