import logging
logger = logging.getLogger(f"axonius.{__name__}")
from jnpr.space import rest, async

import axonius.adapter_exceptions


class JuniperClient:

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

    @staticmethod
    def data_to_xml(rpc_data):
        xml_prefix_string = "<rpc-reply>"
        xml_suffix_string = "</rpc-reply>"
        xml_text_raw = rpc_data.text
        xml_text_location = xml_text_raw.find(xml_prefix_string)
        xml_text_end_location = xml_text_raw.find(xml_suffix_string) + len(xml_suffix_string)
        xml_text = xml_text_raw[xml_text_location:xml_text_end_location]
        return xml_text

    def _do_junus_space_command(self, devices, queue_name, rpc_command, result_name):
        tm = async.TaskMonitor(self.space_rest_client, queue_name, wait_time="10")

        try:
            id_to_name_dict = dict()
            task_ids = []
            for current_device in devices:
                try:
                    logger.info(
                        f"Getting arp from {current_device.name}, {current_device.ipAddr}, {current_device.platform}")
                    result = current_device.exec_rpc_async.post(
                        task_monitor=tm,
                        rpcCommand=rpc_command
                    )
                    id_to_name_dict[str(result.id)] = str(current_device.name)
                    if not result.id > 0:
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
                        yield (result_name, (id_to_name_dict.get(str(pu.taskId), ""), self.data_to_xml(pu.data)))
                except Exception:
                    logger.exception(f"Something is wrong with pu {str(pu)}")
        finally:
            tm.delete()

    def get_all_devices(self):
        devices = self.space_rest_client.device_management.devices.get(
            filter_={'connectionStatus': 'up'})

        final_devices = {}
        for device in devices:
            final_devices[str(device.serialNumber)] = device

        devices = list(final_devices.values())

        for current_device in devices:
            yield ('Juniper Device', current_device)

        yield from self._do_junus_space_command(devices, 'get_arp_q', "<get-arp-table-information/>", 'ARP Device')
        yield from self._do_junus_space_command(devices,
                                                'get_ether_q',
                                                "<get-ethernet-switching-table-information>"
                                                "</get-ethernet-switching-table-information>", 'FDB Device')
