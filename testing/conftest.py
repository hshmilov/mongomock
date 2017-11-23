import pytest

from services.mongo_service import MongoService
from services.core_service import CoreService
from services.aggregator_service import AggregatorService
from services.simple_fixture import initalize_fixture


class AxoniusService(object):
    def __init__(self, db, core, aggregator):
        self.db = db
        self.core = core
        self.aggregator = aggregator

    def get_devices_with_condition(self, cond):
        cursor = self.db.client[self.aggregator.unique_name]['devices_db'].find(
            cond)
        return list(cursor)

    def get_device_by_name(self, adapter_name, device_name):
        cond = {'adapters.{0}.data.name'.format(adapter_name): device_name}
        return self.get_devices_with_condition(cond)


@pytest.fixture(scope="session", autouse=True)
def axonius_fixture(request):
    mongo = MongoService()
    initalize_fixture(request, mongo)

    core = CoreService()
    initalize_fixture(request, core)

    aggregator = AggregatorService()
    initalize_fixture(request, aggregator)

    return AxoniusService(mongo, core, aggregator)
