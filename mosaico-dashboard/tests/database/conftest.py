import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from mosaico_dashboard.db.engine import create_db_engine
from mosaico_dashboard.db.migrate import upgrade_to_head

DEFAULT_URL = "postgresql+psycopg://dashboard:dashboard@localhost:5433/dashboard"
TEST_DATABASE = "dashboard_test"


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """A fresh `dashboard_test` database with all migrations applied."""
    admin_url = os.environ.get("DASHBOARD_TEST_DATABASE_URL", DEFAULT_URL)
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)"))
            c.execute(text(f"CREATE DATABASE {TEST_DATABASE}"))
    except OperationalError:
        pytest.skip(f"Postgres not reachable at {make_url(admin_url).host}")
    finally:
        admin.dispose()
    url = make_url(admin_url).set(database=TEST_DATABASE)
    url_string = url.render_as_string(hide_password=False)
    upgrade_to_head(url_string)
    return url_string


@pytest.fixture
def postgres_engine(postgres_url):
    engine = create_db_engine(postgres_url)
    tables = [t for t in inspect(engine).get_table_names() if t != "alembic_version"]
    if tables:
        with engine.begin() as c:
            c.execute(text(f"TRUNCATE {', '.join(tables)}"))
    yield engine
    engine.dispose()
