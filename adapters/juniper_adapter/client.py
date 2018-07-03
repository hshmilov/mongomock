import logging
logger = logging.getLogger(f"axonius.{__name__}")
from jnpr.space import rest, async

import axonius.adapter_exceptions


class JuniperClient(object):

    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.space_rest_client = rest.Space(self.url, self.username, self.password)
        self.test_connection()

    def test_connection(self):
        try:
            self.space_rest_client.login()

        except Exception as err:
            logger.exception("Failed connecting to Juniper.")
            raise axonius.adapter_exceptions.ClientConnectionException("Failed connecting to Juniper.")
        finally:
            self.space_rest_client.logout()

    def get_all_devices(self):
        devices = self.space_rest_client.device_management.devices.get(
            filter_={'connectionStatus': 'up'})

        for current_device in devices:
            yield ('Juniper Device', current_device)

        tm = async.TaskMonitor(self.space_rest_client, 'get_arp_q')

        try:
            task_ids = []
            for current_device in devices:
                try:
                    logger.info(
                        f"Getting arp from {current_device.name}, {current_device.ipAddr}, {current_device.platform}")
                    result = current_device.exec_rpc_async.post(
                        task_monitor=tm,
                        rpcCommand="<get-arp-table-information/>"
                    )

                    if result.id > 0:
                        logger.error("Async RPC execution Failed. Failed to get arp table from device.")
                        continue

                    task_ids.append(result.id)
                except Exception:
                    logger.exception(f"Got exception with device {current_device.name}")

            # Wait for all tasks to complete
            pu_list = tm.wait_for_tasks(task_ids)
            for pu in pu_list:
                try:
                    if (pu.state != "DONE" or pu.status != "SUCCESS" or
                            str(pu.percentage) != "100.0"):
                        logger.error(
                            f"Async RPC execution Failed. Failed to get arp table from device. The process state was {pu.state}")
                    else:
                        yield ('Arp Device', pu.data)
                except Exception:
                    logger.exception(f"Something is wrong with pu {str(pu)}")
        finally:
            tm.delete()
