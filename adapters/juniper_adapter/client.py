# This module comes from docker file, ignore no mmodule name error
# pylint: disable=E0611
# pylint: disable=import-error
import logging
from collections import defaultdict
import lxml

from jnpr.space import rest, async

logger = logging.getLogger(f'axonius.{__name__}')


def blockify(iter_, blksize, get_division=True):
    result = []
    for item in iter_:
        result.append(item)
        if len(result) == blksize:
            yield result
            result = []
    if result and get_division:
        yield result


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
            try:
                self.space_rest_client.logout()
            except Exception:
                pass

    @staticmethod
    def data_to_xml_async(rpc_data):
        xml_prefix_string = '<rpc-reply>'
        xml_suffix_string = '</rpc-reply>'
        xml_text_raw = rpc_data.text
        xml_text_location = xml_text_raw.find(xml_prefix_string)
        xml_text_end_location = xml_text_raw.find(
            xml_suffix_string) + len(xml_suffix_string)
        xml_text = xml_text_raw[xml_text_location:xml_text_end_location]
        return xml_text

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

    def _do_junus_space_command(self, devices, queue_name, actions, do_async):
        if not do_async:
            yield from self._do_junus_space_command_not_async(devices, queue_name, actions)
        else:
            for device_block in blockify(devices, 100):
                yield from self._do_junus_space_command_async(device_block, queue_name, actions)

    # pylint: disable=too-many-locals
    def _do_junus_space_command_async(self, devices, queue_name, actions):
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
            pu_dict = tm.wait_for_tasks(task_ids)

            juniper_device_actions = [
                'interface list', 'hardware', 'version', 'vlans', 'base-mac']
            juniper_devices = defaultdict(list)
            for id_, pu in pu_dict.items():
                try:
                    rpc_result = getattr(pu, 'exec-rpc-job-result')
                    device_id = str(getattr(rpc_result, 'device-id'))
                    status = str(rpc_result.status).lower()
                    result = rpc_result.result
                    result = lxml.etree.tostring(lxml.objectify.fromstring(str(result)))
                    device_name, action_name = id_to_name_dict.get(id_, ('', ''))
                    if status != 'success':
                        msg = 'Async RPC execution Failed. Failed to get %s from %s. The process state was %s'
                        logger.error(msg, action_name, device_name, status)
                        continue
                    if not device_name or not action_name:
                        logger.warning(f'no such id {id_} {device_id}, ids = {id_to_name_dict.keys()}')
                        continue
                    if action_name in juniper_device_actions:
                        juniper_devices[device_name].append((action_name, result))
                        continue
                    yield (action_name, (device_name, result))
                except Exception:
                    logger.exception(f'Something is wrong with pu {str(pu)}')
            yield from map(lambda x: ('Juniper Device', x), juniper_devices.items())
        finally:
            tm.delete()

    def _do_junus_space_command_not_async(self, devices, queue_name, actions):
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

    def get_all_devices(self, fetch_space_only, do_async, fetch_only_client_info=False):
        devices = self.space_rest_client.device_management.devices.get()
        for current_device in devices:
            yield ('Juniper Space Device', current_device)
        if fetch_space_only:
            return
        up_devices = [device for device in devices if device.connectionStatus == 'up']
        logger.info(f'Number of up devices is {len(up_devices)} out of {len(devices)}')
        if fetch_only_client_info:
            extra_actions = []
        else:
            extra_actions = [
                ('interface list', '<get-interface-information/>'),
                ('hardware', '<get-chassis-inventory/>'),
                ('version', '<get-software-information/>'),
                ('vlans', '<get-ethernet-switching-interface-information>'
                          '<detail/>'
                          '</get-ethernet-switching-interface-information>'),
                ('base-mac', '<get-chassis-mac-addresses/>'),
            ]
        client_actions = [('LLDP Device', '<get-lldp-neighbors-information/>'),
                          ('ARP Device', '<get-arp-table-information/>'),
                          ('FDB Device', '<get-ethernet-switching-table-information/>')]
        actions = extra_actions + client_actions
        yield from self._do_junus_space_command(up_devices, 'get_info_q', actions, do_async)
