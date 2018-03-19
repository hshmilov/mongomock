import pytest
from retrying import retry

from test_helpers.adapter_test_base import AdapterTestBase
from test_helpers.utils import try_until_not_thrown
from test_credentials.test_ad_credentials import *
import time

# These might look like we don't use them but in fact we do. once they are imported, a module-level fixture is run.
from services.adapters.ad_service import AdService, ad_fixture
from services.dns_conflicts_service import DnsConflictsService, dns_conflicts_fixture
from services.general_info_service import general_info_fixture
from services.execution_service import execution_fixture

CLIENT_ID_1_ADMIN_SID = "S-1-5-21-4050441107-50035988-2732102988-500"
CLIENT_ID_1_ADMIN_CAPTION = "Administrator@TestDomain.test"


class TestAdAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AdService()

    @property
    def adapter_name(self):
        return 'ad_adapter'

    @property
    def some_client_id(self):
        return ad_client1_details['dc_name']

    @property
    def some_client_details(self):
        return ad_client1_details

    @property
    def some_device_id(self):
        return DEVICE_ID_FOR_CLIENT_1

    @property
    def some_user_id(self):
        return USER_ID_FOR_CLIENT_1

    def test_fetch_devices(self):
        # Adding first client
        client_id_1 = ad_client1_details['dc_name']
        self.adapter_service.add_client(ad_client1_details)

        # Adding second client
        # client_id_2 = ad_client2_details['dc_name']
        # self.axonius_system.add_client_to_adapter(self.adapter_service, ad_client2_details)

        # Checking that we have devices from both clients
        self.axonius_system.assert_device_aggregated(self.adapter_service, [(client_id_1, DEVICE_ID_FOR_CLIENT_1)])
        # Testing the ability to filter old devices
        devices_list = self.axonius_system.get_devices_with_condition({"adapters.data.hostname": "nonExistance"})
        assert len(devices_list) == 0, "Found device that should have been filtered"
        # self.axonius_system.assert_device_aggregated(self.adapter_service, client_id_2, DEVICE_ID_FOR_CLIENT_2)

    def test_fetch_users(self):
        # I'm going to assume this has already been aggregated. TODO: Change test_fetch_devices to test_fetch_data
        # and check that there.
        devices_list = self.axonius_system.get_users_with_condition(
            {
                "adapters.data.username": USER_ID_FOR_CLIENT_1,
                "adapters.data.sid": USER_SID_FOR_CLIENT_1
            }
        )
        assert len(devices_list) == 1, f"Did not find user {USER_ID_FOR_CLIENT_1}"

    def test_ip_resolving(self):
        self.adapter_service.resolve_ip()
        self.axonius_system.aggregator.query_devices(adapter_id=self.adapter_service.unique_name)

        def assert_ip_resolved():
            self.axonius_system.aggregator.query_devices(adapter_id=self.adapter_service.unique_name)
            interfaces = self.axonius_system.get_device_network_interfaces(self.adapter_service.unique_name,
                                                                           DEVICE_ID_FOR_CLIENT_1)
            assert len(interfaces) > 0

        try_until_not_thrown(50, 5, assert_ip_resolved)

    def test_dns_conflicts(self, dns_conflicts_fixture):
        dns_conflicts_fixture.triggerable_execute_enable()
        dns_conflicts_fixture.find_conflicts()

        @retry(wait_fixed=500,
               stop_max_delay=15000)
        def has_ip_conflict_tag():
            dns_conflicts_fixture.find_conflicts()
            assert len(self.axonius_system.get_devices_with_condition(
                {"tags.name": "IP Conflicts", "tags.type": "label"})) > 0
            assert len(self.axonius_system.get_devices_with_condition(
                {
                    "tags": {
                        '$elemMatch': {
                            "name": "IP Conflicts",
                            "type": "data",
                            "data": {"$ne": "False"}
                        }
                    }
                }
            )) > 0

        has_ip_conflict_tag()

    def test_ad_execute_wmi_smb(self):
        device = self.axonius_system.get_device_by_id(self.adapter_service.unique_name, self.some_device_id)[0]
        internal_axon_id = device['internal_axon_id']

        action_id = self.axonius_system.execution.make_action("execute_wmi_smb",
                                                              internal_axon_id,
                                                              {"wmi_smb_commands": [
                                                                  {"type": "query", "args": [
                                                                      "select SID from Win32_UserProfile"]},
                                                                  {"type": "query", "args": [
                                                                      "select SID from Win32_UserAccount"]}
                                                              ]},
                                                              adapters_to_whitelist=["ad_adapter"])

        def check_execute_wmi_results():
            # Get the first action from the action list ([0])
            action_data = self.axonius_system.execution.get_action_data(self.axonius_system.db, action_id)[0]
            assert action_data["result"] == "Success"
            assert action_data["status"] == "finished"
            assert len(action_data["product"]) == 2  # We queried for 2 queries, assert we have 2 answers.
            assert action_data["product"][0]["status"] == "ok" and action_data["product"][1]["status"] == "ok"

            sids = []
            # [0] is for getting the answer for the first wmi query
            for user in action_data["product"][0]["data"]:
                sids.append(user["SID"])

            # Lets validate we have the special SID's...
            assert "S-1-5-18" in sids  # Local System
            assert "S-1-5-19" in sids  # NT Authority - Local Service
            assert "S-1-5-20" in sids  # NT Authority - Network Service

        try_until_not_thrown(15, 5, check_execute_wmi_results)

    def test_ad_execute_shell(self):
        device = self.axonius_system.get_device_by_id(self.adapter_service.unique_name, self.some_device_id)[0]
        internal_axon_id = device['internal_axon_id']

        action_id = self.axonius_system.execution.make_action("execute_shell",
                                                              internal_axon_id,
                                                              {"shell_commands": {"Windows": [
                                                                  r"dir c:\windows\system32\drivers\etc",
                                                                  r"dir c:\windows\system32\*.exe"
                                                              ]}},
                                                              adapters_to_whitelist=["ad_adapter"])

        def check_execute_shell_results():
            action_data = self.axonius_system.execution.get_action_data(self.axonius_system.db, action_id)[0]
            assert action_data["result"] == "Success"
            assert action_data["status"] == "finished"

            # The following is a file that is always present in c:\windows\system32\drivers\etc\
            assert action_data["product"][0]["status"] == "ok"
            assert "lmhosts.sam" in action_data["product"][0]["data"]
            # The following is a file that is always present in c:\windows\system32
            assert action_data["product"][1]["status"] == "ok"
            assert "cmd.exe" in action_data["product"][1]["data"]

        try_until_not_thrown(15, 5, check_execute_shell_results)

    def test_ad_file_operations(self):
        # We must remember this runs in parallel. So the filename is going to be random.
        device = self.axonius_system.get_device_by_id(self.adapter_service.unique_name, self.some_device_id)[0]
        internal_axon_id = device['internal_axon_id']
        file1_name = f"axonius_test1_{time.time()}.txt"
        file2_name = f"axonius_test2_{time.time()}.txt"

        # 1. Put the files
        action_id = self.axonius_system.execution.make_action("put_files",
                                                              internal_axon_id,
                                                              {
                                                                  "files_path": [file1_name, file2_name],
                                                                  "files_content": ["abcd", "efgh"]
                                                              },
                                                              adapters_to_whitelist=["ad_adapter"])

        def check_put_files_results():
            action_data = self.axonius_system.execution.get_action_data(self.axonius_system.db, action_id)[0]
            assert action_data["result"] == "Success"
            assert action_data["status"] == "finished"
            assert len(action_data["product"]) == 2
            assert action_data["product"][0]["status"] == "ok" and action_data["product"][1]["status"] == "ok"
            assert action_data["product"][0]["data"] is True and action_data["product"][1]["data"] is True

        try_until_not_thrown(15, 5, check_put_files_results)

        # 2. Get the files
        action_id = self.axonius_system.execution.make_action("get_files",
                                                              internal_axon_id,
                                                              {
                                                                  "files_path": [file1_name, file2_name]
                                                              },
                                                              adapters_to_whitelist=["ad_adapter"])

        def check_get_files_results():
            action_data = self.axonius_system.execution.get_action_data(self.axonius_system.db, action_id)[0]
            assert action_data["result"] == "Success"
            assert action_data["status"] == "finished"
            assert len(action_data["product"]) == 2
            assert action_data["product"][0]["status"] == "ok" and action_data["product"][1]["status"] == "ok"
            assert action_data["product"][0]["data"] == "abcd" and action_data["product"][1]["data"] == "efgh"

        try_until_not_thrown(15, 5, check_get_files_results)

        # 3. Delete the files
        action_id = self.axonius_system.execution.make_action("delete_files",
                                                              internal_axon_id,
                                                              {
                                                                  "files_path": [file1_name, file2_name]
                                                              },
                                                              adapters_to_whitelist=["ad_adapter"])

        def check_delete_files_results():
            action_data = self.axonius_system.execution.get_action_data(self.axonius_system.db, action_id)[0]
            assert action_data["result"] == "Success"
            assert action_data["status"] == "finished"
            assert len(action_data["product"]) == 2
            assert action_data["product"][0]["status"] == "ok" and action_data["product"][1]["status"] == "ok"
            assert action_data["product"][0]["data"] is True and action_data["product"][1]["data"] is True

        try_until_not_thrown(15, 5, check_delete_files_results)

        # 4. Try to get the files again. This should fail
        # 3. Delete the files
        action_id = self.axonius_system.execution.make_action("get_files",
                                                              internal_axon_id,
                                                              {
                                                                  "files_path": [file1_name, file2_name]
                                                              },
                                                              adapters_to_whitelist=["ad_adapter"])

        def check_get_files_after_delete_results():
            action_data = self.axonius_system.execution.get_action_data(self.axonius_system.db, action_id)[0]
            assert action_data["result"] == "Failure"
            assert len(action_data["product"]) == 2
            assert action_data["product"][0]["status"] == "exception"
            assert action_data["product"][1]["status"] == "exception"
            # file not found errors
            assert "STATUS_OBJECT_NAME_NOT_FOUND" in action_data["product"][0]["data"]
            assert "STATUS_OBJECT_NAME_NOT_FOUND" in action_data["product"][1]["data"]

        try_until_not_thrown(15, 5, check_get_files_after_delete_results)
