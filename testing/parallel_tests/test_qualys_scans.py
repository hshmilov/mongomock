
# pylint: disable=W0611
from services.adapters.qualys_scans_service import (QualysScansService,
                                                    qualys_scans_fixture)
from test_credentials.test_qualys_scans_credentials import CLIENT_DETAILS, SOME_DEVICE_ID
from test_helpers.adapter_test_base import AdapterTestBase


def _get_id_from_client(client):
    return client['Qualys_Scans_Domain']


class TestQualysScansAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return QualysScansService()

    @property
    def some_client_id(self):
        return _get_id_from_client(CLIENT_DETAILS[0])

    @property
    def some_user_id(self):
        raise NotImplementedError

    @property
    def some_client_details(self):
        return CLIENT_DETAILS[0]

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    def test_fetch_devices(self):
        some_client, some_adapters_ids = CLIENT_DETAILS
        some_client_id = _get_id_from_client(some_client)
        self.adapter_service.add_client(some_client)
        for some_adapters_id in some_adapters_ids:
            self.axonius_system.assert_device_aggregated(
                self.adapter_service,
                [(some_client_id, some_adapters_id)]
            )
