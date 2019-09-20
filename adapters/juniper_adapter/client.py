# This module comes from docker file, ignore no mmodule name error
# pylint: disable=E0611
# pylint: disable=import-error
import logging
from collections import defaultdict
import lxml

from jnpr.space import rest

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
        xml_prefix_string = '<replyMsgData>'
        xml_suffix_string = '</replyMsgData>'
        xml_text_raw = rpc_data
        xml_text_location = xml_text_raw.find(xml_prefix_string) + len(xml_prefix_string)
        xml_text_end_location = xml_text_raw.find(xml_suffix_string)
        xml_text = xml_text_raw[xml_text_location:xml_text_end_location]
        xml_text = '<rpc-reply>' + xml_text + '</rpc-reply>'
        return xml_text

    def _do_junus_space_command(self, devices, queue_name, actions):
        juniper_device_actions = [
            'interface list', 'hardware', 'version', 'vlans', 'base-mac']
        juniper_devices = defaultdict(list)
        for current_device in devices:
            device_name = str(current_device.name)
            for action_name, action_cmd in actions:
                try:
                    logger.info(
                        f'Getting {action_name} from'
                        f' {current_device.name}, {current_device.ipAddr}, {current_device.platform}')
                    result = current_device.exec_rpc.post(
                        rpcCommand=action_cmd
                    )
                    result = lxml.etree.tostring(result, xml_declaration=True).decode()
                    if '<status>Success</status>' not in result:
                        logger.warning(f'exec rpc failed {result}')
                        continue

                    result = self.data_to_xml(result)

                    if action_name in juniper_device_actions:
                        juniper_devices[device_name].append((action_name, result))
                        continue

                    yield (action_name, (device_name, result))
                except Exception:
                    logger.exception(
                        f'Got exception with device {current_device.name}')
            yield from map(lambda x: ('Juniper Device', x), juniper_devices.items())

    def get_all_devices(self):
        devices = self.space_rest_client.device_management.devices.get()
        for current_device in devices:
            yield ('Juniper Space Device', current_device)

        up_devices = [device for device in devices if device.connectionStatus == 'up']
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

        yield from self._do_junus_space_command(up_devices, 'get_info_q', actions)
