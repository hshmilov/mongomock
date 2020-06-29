import json
import uuid

from services.adapters.google_mdm_service import GoogleMdmService, google_mdm_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_google_mdm_credentials import *
from google_mdm_adapter.service import GoogleMdmAdapter
import pytest


class TestGoogleMdmAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return GoogleMdmService()

    @property
    def some_client_id(self):
        return service_json_data['client_id']

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
            'account_to_impersonate': account_to_impersonate
        }

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @pytest.mark.skip("No reachability test")
    def test_check_reachability(self):
        pass
