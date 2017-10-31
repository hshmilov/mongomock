import pytest
from retrying import retry

from services.mongo_service import mongo_fixture


def test_mongo_up(mongo_fixture):
    @retry(wait_fixed=100, stop_max_attempt_number=60)
    def check_if_up():
        assert mongo_fixture.is_up()

    check_if_up()
