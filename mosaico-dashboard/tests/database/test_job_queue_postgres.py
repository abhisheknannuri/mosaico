import pytest

from mosaico_dashboard.db.jobs import claim_next, enqueue

pytestmark = pytest.mark.database


def test_concurrent_claims_never_take_the_same_job(postgres_engine):
    with postgres_engine.begin() as c:
        enqueue(c, "ingest", {"n": 1})
        enqueue(c, "ingest", {"n": 2})

    with postgres_engine.connect() as first, postgres_engine.connect() as second:
        with first.begin(), second.begin():
            a = claim_next(first)
            b = claim_next(second)
            third = claim_next(second)

    assert a is not None and b is not None
    assert a.id != b.id
    assert third is None


def test_only_one_worker_holds_the_lock(postgres_url):
    from mosaico_dashboard.db.engine import create_db_engine
    from mosaico_dashboard.db.workers import release_worker_lock, take_worker_lock

    engine = create_db_engine(postgres_url)
    first = take_worker_lock(engine)
    second = take_worker_lock(engine)

    assert first is not None
    assert second is None
    release_worker_lock(first)
    third = take_worker_lock(engine)
    assert third is not None
    release_worker_lock(third)
    engine.dispose()


def test_setting_upsert(postgres_engine):
    from mosaico_dashboard.db.settings import delete_setting, get_setting, set_setting

    with postgres_engine.begin() as c:
        set_setting(c, "test_key", "a")
        set_setting(c, "test_key", "b")
        assert get_setting(c, "test_key") == "b"
        delete_setting(c, "test_key")
        assert get_setting(c, "test_key") is None
