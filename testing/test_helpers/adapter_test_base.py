import uuid
from datetime import datetime, timezone, timedelta

import pytest
from axonius.consts.plugin_consts import AGGREGATOR_PLUGIN_NAME

from services.axonius_service import get_service
from test_helpers.utils import check_conf


class AdapterTestBase(object):
    """
    Basic tests for adapter are defined here.
    If one wants to skip or modify a test he can do that by overriding the corresponding method.
    If one wants to skip a test - he can do that by overriding and marking the test with @pytest.mark.skip
    """
    axonius_system = get_service()

    @property
    def adapter_service(self):
        raise NotImplementedError

    @property
    def adapter_name(self):
        raise NotImplementedError

    @property
    def some_client_id(self):
        raise NotImplementedError

    @property
    def some_client_details(self):
        raise NotImplementedError

    @property
    def some_device_id(self):
        raise NotImplementedError

    def drop_clients(self):
        self.axonius_system.db.client[self.adapter_service.unique_name].drop_collection('clients')

    def test_adapter_is_up(self):
        assert self.adapter_service.is_up()

    def test_adapter_responds_to_schema(self):
        assert self.adapter_service.schema().status_code == 200

    def test_adapter_in_configs(self):
        check_conf(self.axonius_system, self.adapter_service, self.adapter_name)

    def test_check_registration(self):
        assert self.adapter_service.is_plugin_registered(self.axonius_system.core)

    def test_fetch_devices(self):
        self.adapter_service.add_client(self.some_client_details)
        self.axonius_system.assert_device_aggregated(self.adapter_service, [(self.some_client_id, self.some_device_id)])

    def test_devices_cleaning(self):
        self.adapter_service.trigger_clean_db()  # first clean might not be empty
        cleaned_count = self.adapter_service.trigger_clean_db()
        assert cleaned_count == 0  # second clean should have no devices cleaned

        now = datetime.now(tz=timezone.utc)
        long_time_ago = now - timedelta(days=360)
        devices_db = self.axonius_system.db.client[AGGREGATOR_PLUGIN_NAME]['devices_db']

        # this is a fake device that is "new" from "now"
        devices_db.insert_one({
            "internal_axon_id": "1-" + uuid.uuid4().hex,
            "accurate_for_datetime": now,
            "adapters": [
                {
                    "client_used": "SomeClient",
                    "plugin_type": "Adapter",
                    "plugin_name": self.adapter_service.plugin_name,
                    "plugin_unique_name": self.adapter_service.unique_name,
                    "accurate_for_datetime": now,
                    "data": {
                        "id": "2-" + uuid.uuid4().hex,
                        "raw": {
                        },
                    }
                }
            ],
            "tags": []
        })
        cleaned_count = self.adapter_service.trigger_clean_db()
        assert cleaned_count == 0  # the device added shouldn't be removed

        # this is a fake device from a "long time ago"
        deleted_device_id = "3-" + uuid.uuid4().hex
        devices_db.insert_one({
            "internal_axon_id": deleted_device_id,
            "accurate_for_datetime": now,
            "adapters": [
                {
                    "client_used": "SomeClient",
                    "plugin_type": "Adapter",
                    "plugin_name": self.adapter_service.plugin_name,
                    "plugin_unique_name": self.adapter_service.unique_name,
                    "accurate_for_datetime": long_time_ago,
                    "data": {
                        "id": "4-" + uuid.uuid4().hex,
                        "raw": {
                        },
                    }
                }
            ],
            "tags": []
        })
        cleaned_count = self.adapter_service.trigger_clean_db()
        assert cleaned_count == 1  # the device added is old and should be deleted
        assert devices_db.count({'internal_axon_id': deleted_device_id}) == 0

        deleted_device_id = "5-" + uuid.uuid4().hex
        deleted_adapter_device_id = "6-" + uuid.uuid4().hex
        not_deleted_adapter_device_id = "7-" + uuid.uuid4().hex
        devices_db.insert_one({
            "internal_axon_id": deleted_device_id,
            "accurate_for_datetime": now,
            "adapters": [
                {
                    "client_used": "SomeClient",
                    "plugin_type": "Adapter",
                    "plugin_name": self.adapter_service.plugin_name,
                    "plugin_unique_name": self.adapter_service.unique_name,
                    "accurate_for_datetime": long_time_ago,
                    "data": {
                        "id": deleted_adapter_device_id,
                        "raw": {
                        },
                    }
                },
                {
                    "client_used": "SomeClientFromAnotherAdapter",
                    "plugin_type": "Adapter",
                    "plugin_name": "high_capacity_carburetor_adapter",
                    "plugin_unique_name": "high_capacity_carburetor_adapter_1337",
                    "accurate_for_datetime": now,
                    "data": {
                        "raw": {
                        },
                        "id": not_deleted_adapter_device_id,
                    }
                }
            ],
            "tags": []
        })

        cleaned_count = self.adapter_service.trigger_clean_db()
        assert cleaned_count == 1  # the device added is old and should be deleted
        # only one of the adapter_devices should be removed, so the axonius device should stay
        assert devices_db.count({'adapters.data.id': not_deleted_adapter_device_id}) == 1
        # verify our device is deleted
        assert devices_db.count({'adapters.data.id': deleted_adapter_device_id}) == 0

        # this is a fake device from a "long time ago" according to last `seen_but` not `accurate_for_datetime`
        deleted_device_id = "8-" + uuid.uuid4().hex
        devices_db.insert_one({
            "internal_axon_id": deleted_device_id,
            "accurate_for_datetime": now,
            "adapters": [
                {
                    "client_used": "SomeClient",
                    "plugin_type": "Adapter",
                    "plugin_name": self.adapter_service.plugin_name,
                    "plugin_unique_name": self.adapter_service.unique_name,
                    "accurate_for_datetime": now,
                    "data": {
                        "id": "9-" + uuid.uuid4().hex,
                        "last_seen": long_time_ago,
                        "raw": {
                        },
                    }
                }
            ],
            "tags": []
        })
        cleaned_count = self.adapter_service.trigger_clean_db()
        assert cleaned_count == 1  # the device added is old and should be deleted
        assert devices_db.count({'internal_axon_id': deleted_device_id}) == 0

    def test_restart(self):
        service = self.adapter_service
        # it's ok to restart adapter in adapter test
        service.take_process_ownership()
        self.axonius_system.restart_plugin(service)
