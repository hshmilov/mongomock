# pylint: disable=unused-import
import json
import uuid

import pytest

from services.adapters.google_big_query_service import GoogleBigQueryService, google_big_query_fixture
from test_helpers.adapter_test_base import AdapterTestBase
from test_credentials.test_google_big_query_credentials import SOME_DEVICE_ID, GBQ_PROJECT_ID, \
    GBQ_DATASET_ID, SERVICE_JSON_DATA
from google_big_query_adapter.client_id import get_client_id


class TestGoogleBigQueryAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return GoogleBigQueryService()

    @property
    def adapter_name(self):
        return 'google_big_query_adapter'

    @property
    def some_client_id(self):
        return get_client_id(self.some_client_details)

    @property
    def adapter_has_constant_url(self):
        return True

    @property
    def some_client_details(self):
        import gridfs
        fs = gridfs.GridFS(self.axonius_system.db.client[self.adapter_service.unique_name])
        filename = uuid.uuid4().hex
        written_file_uuid = str(fs.put(bytes(json.dumps(SERVICE_JSON_DATA), 'ascii'), filename=filename))
        return {
            'keypair_file': {
                'uuid': written_file_uuid,
                'filename': filename
            },
            'project_id': GBQ_PROJECT_ID,
            'dataset_id': GBQ_DATASET_ID
        }

    @pytest.mark.skip(f'This adapter works only for one customer, so we can not check the query here')
    def test_fetch_devices(self):
        pass

    @property
    def some_device_id(self):
        return SOME_DEVICE_ID

    @property
    def some_user_id(self):
        raise NotImplementedError()
