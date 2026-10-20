from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import inspect, text

from mosaico_dashboard.db.engine import create_db_engine, ping
from mosaico_dashboard.db.migrate import upgrade_to_head

pytestmark = pytest.mark.database


def test_migrations_reach_the_latest_revision(postgres_engine):
    with postgres_engine.connect() as c:
        revision = c.execute(text("SELECT version_num FROM alembic_version")).scalar()

    assert revision == "b4a3c9872c17"
    tables = set(inspect(postgres_engine).get_table_names())
    assert {"job", "worker", "alembic_version"} <= tables


def test_migrating_again_changes_nothing(postgres_url):
    upgrade_to_head(postgres_url)
    upgrade_to_head(postgres_url)


def test_concurrent_migrations_are_serialised(postgres_url):
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda _: upgrade_to_head(postgres_url), range(3)))


def test_ping(postgres_url):
    engine = create_db_engine(postgres_url)

    assert ping(engine) is True
    engine.dispose()
