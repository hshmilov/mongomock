# This module comes from docker file, ignore no mmodule name error
#pylint: disable=E0611
import logging

from collections import defaultdict
from jnpr.space import rest, async

logger = logging.getLogger(f'axonius.{__name__}')


class JuniperClient:

    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.space_rest_client = rest.Space(
            self.url, self.username, self.password)
        self.test_connection()

    def test_connection(self):
        try:
            self.space_rest_client.login()
            devices = self.space_rest_client.device_management.devices.get(
                filter_={'connectionStatus': 'up'})
        finally:
            self.space_rest_client.logout()

    @staticmethod
    def data_to_xml(rpc_data):
        xml_prefix_string = '<rpc-reply>'
        xml_suffix_string = '</rpc-reply>'
        xml_text_raw = rpc_data.text
        xml_text_location = xml_text_raw.find(xml_prefix_string)
        xml_text_end_location = xml_text_raw.find(
            xml_suffix_string) + len(xml_suffix_string)
        xml_text = xml_text_raw[xml_text_location:xml_text_end_location]
        return xml_text

    def _do_junus_space_command(self, devices, queue_name, actions):
        tm = async.TaskMonitor(self.space_rest_client,
                               queue_name, wait_time='10')

        try:
            id_to_name_dict = dict()
            task_ids = []
            for current_device in devices:
                for action_name, action_cmd in actions:
                    try:
                        logger.info(
                            f'Getting {action_name} from'
                            f' {current_device.name}, {current_device.ipAddr}, {current_device.platform}')
                        result = current_device.exec_rpc_async.post(
                            task_monitor=tm,
                            rpcCommand=action_cmd
                        )
                        id_to_name_dict[str(result.id)] = (
                            str(current_device.name), action_name)
                        if not result.id > 0:
                            logger.error(
                                'Async RPC execution Failed. Failed to get arp table from device.')
                            continue

                        task_ids.append(result.id)
                    except Exception:
                        logger.exception(
                            f'Got exception with device {current_device.name}')

            # Wait for all tasks to complete
            pu_list = tm.wait_for_tasks(task_ids)

            juniper_device_actions = [
                'interface list', 'hardware', 'version', 'vlans', 'base-mac']
            juniper_devices = defaultdict(list)
            for pu in pu_list:
                try:
                    device_name, action_name = id_to_name_dict.get(
                        str(pu.taskId), ('', ''))

                    if (pu.state != 'DONE' or pu.status != 'SUCCESS' or
                            str(pu.percentage) != '100.0'):
                        logger.error(
                            'Async RPC execution Failed. Failed to get %s from %s. The process state was %s',
                            action_name, device_name, pu.state)
                        continue

                    if action_name in juniper_device_actions:
                        juniper_devices[device_name].append(
                            (action_name, self.data_to_xml(pu.data)))
                        continue

                    yield (action_name, (device_name, self.data_to_xml(pu.data)))
                except Exception:
                    logger.exception(f'Something is wrong with pu {str(pu)}')

            yield from map(lambda x: ('Juniper Device', x), juniper_devices.items())

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
            yield ('Juniper Space Device', current_device)

        actions = [
            ('LLDP Device', '<get-lldp-neighbors-information/>'),
            ('ARP Device', '<get-arp-table-information/>'),
            ('FDB Device', '<get-ethernet-switching-table-information/>'),
            ('interface list', '<get-interface-information/>'),
            ('hardware', '<get-chassis-inventory/>'),
            ('version', '<get-software-information/>'),
            ('vlans', '<get-ethernet-switching-interface-information>'
                      '<detail/>'
                      '</get-ethernet-switching-interface-information>'),
            ('base-mac', '<get-chassis-mac-addresses/>'),
        ]

        yield from self._do_junus_space_command(devices, 'get_info_q', actions)
