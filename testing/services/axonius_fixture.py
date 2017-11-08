import pytest

from services.mongo_service import MongoService
from services.core_service import CoreService
from services.aggregator_service import AggregatorService
from services.simple_fixture import initalize_fixture


@pytest.fixture(scope="session")
def axonius_fixture(request):
    mongo = MongoService()
    initalize_fixture(request, mongo)

    core = CoreService()
    initalize_fixture(request, core)

    aggregator = AggregatorService()
    initalize_fixture(request, aggregator)

    return {'db': mongo, 'core': core, 'aggregator': aggregator}
