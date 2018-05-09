from retrying import retry

from test_helpers.adapter_test_base import AdapterTestBase
from test_helpers.utils import try_until_not_thrown
from test_credentials.test_ad_credentials import *
import time

# These might look like we don't use them but in fact we do. once they are imported, a module-level fixture is run.
from services.adapters.ad_service import AdService, ad_fixture
from services.plugins.device_control_service import device_control_fixture


class TestAdAdapter(AdapterTestBase):
    @property
    def adapter_service(self):
        return AdService()

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

        # TODO: AD Adapter will no longer check `last_seen` so no devices will be filtered out from
        # /devices, this test should be moved elsewhere

        # Testing the ability to filter old devices
        # devices_list = self.axonius_system.get_devices_with_condition({"adapters.data.hostname": "nonExistance"})
        # assert len(devices_list) == 0, "Found device that should have been filtered"
        # # self.axonius_system.assert_device_aggregated(self.adapter_service, client_id_2, DEVICE_ID_FOR_CLIENT_2)

        # Check Printers
        printers_list = self.axonius_system.get_devices_with_condition(
            {
                "adapters.data.id": DEVICE_ID_FOR_CLIENT_1,
                "adapters.data.ad_printers.name": PRINTER_NAME_FOR_CLIENT1
            }
        )
        assert len(printers_list) == 1, f"Did not find printer {PRINTER_NAME_FOR_CLIENT1}"

        # Check DC
        dc_list = self.axonius_system.get_devices_with_condition(
            {
                "adapters.data.id": CLIENT1_DC1_ID,
                "adapters.data.ad_is_dc": True,
                "adapters.data.ad_dc_gc": True,
                "adapters.data.ad_dc_infra_master": True,
                "adapters.data.ad_dc_rid_master": True,
                "adapters.data.ad_dc_pdc_emulator": True,
                "adapters.data.ad_dc_naming_master": True,
                "adapters.data.ad_dc_schema_master": True,
                "adapters.data.ad_dc_is_dhcp_server": False,
                "adapters.data.ad_dfsr_shares.name": "Tools",
                "adapters.data.ad_site_name": "TestDomain-TelAviv",
                "adapters.data.ad_site_location": "Tel Aviv",
                "adapters.data.ad_subnet": "192.168.20.0/24"
            }
        )

        assert len(dc_list) == 1, f"device {CLIENT1_DC1_ID} hasn't been filled with all AD info"

        # Check Exchange Servers
        exchange_servers_list = self.axonius_system.get_devices_with_condition(
            {
                "adapters.data.id": CLIENT1_DC4_ID,
                "adapters.data.ad_exchange_server_product_id": "02064-004-0074055-02417"
            }
        )

        assert len(exchange_servers_list) == 1, f"device {CLIENT1_DC4_ID} is not an exchange server, but it should be!"

    def test_fetch_users(self):
        # I'm going to assume this has already been aggregated. TODO: Change test_fetch_devices to test_fetch_data
        # and check that there.
        users_list = self.axonius_system.get_users_with_condition(
            {
                "adapters.data.username": USER_ID_FOR_CLIENT_1,
                "adapters.data.ad_sid": USER_SID_FOR_CLIENT_1
            }
        )
        assert len(users_list) == 1, f"Did not find user {USER_ID_FOR_CLIENT_1}"

    def test_ip_resolving(self):
        self.adapter_service.resolve_ip()
        self.axonius_system.aggregator.query_devices(adapter_id=self.adapter_service.unique_name)

        def assert_ip_resolved():
            self.axonius_system.aggregator.query_devices(adapter_id=self.adapter_service.unique_name)
            interfaces = self.axonius_system.get_device_network_interfaces(self.adapter_service.unique_name,
                                                                           DEVICE_ID_FOR_CLIENT_1)
            assert len(interfaces) > 0

        try_until_not_thrown(50, 5, assert_ip_resolved)

    def test_report_generator(self):
        self.adapter_service.generate_report()

        def assert_report_generated():
            report = self.axonius_system.db_find(self.adapter_service.unique_name,
                                                 "report",
                                                 {"name": "report", "data": {"$exists": True}})
            assert len(report) > 0

        try_until_not_thrown(50, 5, assert_report_generated)

    def test_dns_conflicts(self):
        @retry(wait_fixed=5000,
               stop_max_delay=125000)  # it can take up to 2 minutes for the tag to appear
        def has_ip_conflict_tag():
            assert len(self.axonius_system.get_devices_with_condition(
                {
                    "tags": {
                        '$elemMatch': {
                            "name": "IP Conflicts",
                            "type": "label",
                            "data": {"$ne": False}
                        }
                    }
                }
            )) > 0
            assert len(self.axonius_system.get_devices_with_condition(
                {
                    "tags": {
                        '$elemMatch': {
                            "name": "IP Conflicts",
                            "type": "data",
                            "data": {"$ne": False}
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
                                                              adapters_to_whitelist=["active_directory_adapter"])

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
                                                              adapters_to_whitelist=["active_directory_adapter"])

        def check_execute_shell_results():
            action_data = self.axonius_system.execution.get_action_data(self.axonius_system.db, action_id)[0]
            assert action_data["result"] == "Success"
            assert action_data["status"] == "finished"

            # Put these in their own variables to that a failure will show them in teamcity.
            product_0_status = action_data["product"][0]["status"]
            product_0_data = action_data["product"][0]["data"]
            product_1_status = action_data["product"][1]["status"]
            product_1_data = action_data["product"][1]["data"]

            # The following is a file that is always present in c:\windows\system32\drivers\etc\
            assert product_0_status == "ok"
            assert "lmhosts.sam" in product_0_data
            # The following is a file that is always present in c:\windows\system32
            assert product_1_status == "ok"
            assert "cmd.exe" in product_1_data

        try_until_not_thrown(15, 5, check_execute_shell_results)

    def test_ad_execute_binary(self):
        device = self.axonius_system.get_device_by_id(self.adapter_service.unique_name, self.some_device_id)[0]
        internal_axon_id = device['internal_axon_id']

        action_id = self.axonius_system.execution.make_action(
            "execute_binary",
            internal_axon_id,
            {
                "binary_file_path": TEST_BINARY_LOCATION,
                "binary_params": "\"Hello, World\""
            },
            adapters_to_whitelist=["active_directory_adapter"])

        def check_execute_binary_results():
            action_data = self.axonius_system.execution.get_action_data(self.axonius_system.db, action_id)[0]
            assert action_data["result"] == "Success"
            assert action_data["status"] == "finished"

            # The following is a file that is always present in c:\windows\system32\drivers\etc\
            assert action_data["product"][0]["status"] == "ok"
            assert "Hello, World" in action_data["product"][0]["data"]

        try_until_not_thrown(15, 5, check_execute_binary_results)

    def test_ad_execute_shell_by_device_control(self, device_control_fixture):
        # TODO: We should have a parallel test for device control but this is complicated now.
        device = self.axonius_system.get_device_by_id(self.adapter_service.unique_name, self.some_device_id)[0]
        internal_axon_id = device['internal_axon_id']

        device_control_fixture.run_action(
            {
                "action_name": "Test Action",
                "action_type": "shell",
                "command": r"dir c:\windows\system32\drivers\etc",
                "internal_axon_ids": [internal_axon_id]
            }
        )

        @retry(wait_fixed=7000,
               stop_max_delay=15000)
        def has_run_shell_success_tags():
            result = self.axonius_system.get_devices_with_condition(
                {
                    "tags": {
                        '$elemMatch': {
                            "name": "Action 'Test Action' Success",
                            "type": "label",
                            "data": {"$ne": "False"}
                        }
                    }
                })
            assert len(result) > 0, str(result)
            result = self.axonius_system.get_devices_with_condition(
                {
                    "tags": {
                        '$elemMatch': {
                            "name": "Action 'Test Action'",
                            "type": "data",
                            "data": {"$regex": ".*lmhosts\.sam.*"}
                        }
                    }
                }
            )
            assert len(result) > 0, self.axonius_system.get_devices_with_condition(
                {
                    "tags": {
                        '$elemMatch': {
                            "name": "Action 'Test Action'",
                            "type": "data"
                        }
                    }
                })

        has_run_shell_success_tags()

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
                                                              adapters_to_whitelist=["active_directory_adapter"])

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
                                                              adapters_to_whitelist=["active_directory_adapter"])

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
                                                              adapters_to_whitelist=["active_directory_adapter"])

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
                                                              adapters_to_whitelist=["active_directory_adapter"])

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
