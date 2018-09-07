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
        return service_json_data['client_id']

    @property
    def some_client_details(self):
        import gridfs
        fs = gridfs.GridFS(self.axonius_system.db.client[self.adapter_service.unique_name])
        filename = uuid.uuid4().hex
        written_file_uuid = str(fs.put(bytes(json.dumps(service_json_data), 'ascii'), filename=filename))
        return {
            'keypair_file': {
                'uuid': written_file_uuid,
                'filename': filename
            },
        }

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass
