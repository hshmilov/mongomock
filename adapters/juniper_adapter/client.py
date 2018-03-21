from jnpr.space import rest, async

import axonius.adapter_exceptions


class JuniperClient(object):

    def __init__(self, logger, url, username, password):
        self.logger = logger
        self.url = url
        self.username = username
        self.password = password
        self.space_rest_client = rest.Space(self.url, self.username, self.password)
        self.test_connection()

    def test_connection(self):
        try:
            self.space_rest_client.login()

        except Exception as err:
            self.logger.exception("Failed connecting to Juniper.")
            raise axonius.adapter_exceptions.ClientConnectionException("Failed connecting to Juniper.")
        finally:
            self.space_rest_client.logout()

    def get_all_devices(self):
        devices = self.space_rest_client.device_management.devices.get(
            filter_={'deviceFamily': 'junos', 'connectionStatus': 'up'})

        tm = async.TaskMonitor(self.space_rest_client, 'get_arp_q')
        raw_data = []

        try:
            task_ids = []
            for current_device in devices:
                raw_data.append(('juniper_device', current_device))
                self.logger.info(
                    f"Getting arp from {current_device.name}, {current_device.ipAddr}, {current_device.platform}")
                result = current_device.exec_rpc_async.post(
                    task_monitor=tm,
                    rpcCommand="<get-arp-table-information/>"
                )

                if result.id > 0:
                    self.logger.error("Async RPC execution Failed. Failed to get arp table from device.")
                    continue

                task_ids.append(result.id)

            # Wait for all tasks to complete
            pu_list = tm.wait_for_tasks(task_ids)
            for pu in pu_list:
                if (pu.state != "DONE" or pu.status != "SUCCESS" or
                        str(pu.percentage) != "100.0"):
                    self.logger.error(
                        f"Async RPC execution Failed. Failed to get arp table from device. The process state was {pu.state}")

                # Print the RPC result for each
                raw_data.append(('arp_device', pu.data))
        finally:
            tm.delete()

        return raw_data
