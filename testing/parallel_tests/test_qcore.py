import pytest

from qcore_mongo import QcoreMongo
from services.adapters.qcore_service import QcoreService, qcore_fixture

from test_helpers.adapter_test_base import AdapterTestBase

from test_helpers.qcore_fake_pump import QcoreFakePump
from test_helpers.utils import try_until_not_thrown


class TestQcoreAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return QcoreService()

    @property
    def adapter_name(self):
        return 'qcore_adapter'

    @property
    def some_client_id(self):
        return "1"

    @property
    def some_client_details(self):
        return {"mediator": "1"}

    @property
    def some_device_id(self):
        return "659"

    def test_fetch_devices(self):
        assert self.adapter_service.is_up()
        pump = QcoreFakePump()
        pump.send_registration()
        pump.send_connectivity_update()
        qcore_db = QcoreMongo()

        try_until_not_thrown(10, 10, lambda: len(list(qcore_db.all_pumps)) > 0)

        self.axonius_system.assert_device_aggregated(self.adapter_service, self.some_client_id, self.some_device_id)


if __name__ == '__main__':
    pytest.main([__file__])
