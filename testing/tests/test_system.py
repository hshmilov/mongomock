import pytest

from services.mongo_service import mongo_fixture
from services.core_service import core_fixture
from services.aggregator_service import aggregator_fixture


def test_system_is_up(mongo_fixture, core_fixture, aggregator_fixture):
    print("system is up")
