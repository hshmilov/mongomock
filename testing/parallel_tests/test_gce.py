import json
import uuid

from services.adapters.gce_service import GceService, gce_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_gce_credentials import *
from gce_adapter.service import GceAdapter
import pytest


class TestGceAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return GceService()

    @property
    def some_client_id(self):
        return service_json_data['client_id'] + '_' + service_json_data['project_id']

    @property
    def some_client_details(self):
        filename = uuid.uuid4().hex
        written_file_uuid = self.axonius_system.db.db_files.upload_file(
            bytes(json.dumps(service_json_data), 'ascii'),
            filename=filename
        )
        return {
            'keypair_file': {
                'uuid': written_file_uuid,
                'filename': filename
            },
        }

    @property
    def adapter_has_constant_url(self):
        return True

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip('AX-7030')
    def test_fetch_devices(self):
        pass
