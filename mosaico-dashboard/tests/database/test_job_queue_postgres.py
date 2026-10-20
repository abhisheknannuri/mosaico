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
