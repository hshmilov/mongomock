import logging
import socket
import struct

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none, parse_bool_from_raw
from f5_big_iq_adapter.client_id import get_client_id
from f5_big_iq_adapter.connection import F5BigIqConnection
from f5_big_iq_adapter.structures import F5BigIqDeviceInstance, DeviceReference, \
    ProfileCollectionReference, ReferenceInfo, ClonePool, SourceAddressTranslation

logger = logging.getLogger(f'axonius.{__name__}')


class F5BigIqAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(F5BigIqDeviceInstance):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = F5BigIqConnection(domain=client_config.get('domain'),
                                       verify_ssl=client_config.get('verify_ssl'),
                                       https_proxy=client_config.get('https_proxy'),
                                       proxy_username=client_config.get('proxy_username'),
                                       proxy_password=client_config.get('proxy_password'),
                                       username=client_config.get('username'),
                                       password=client_config.get('password'))
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config.get('domain'), str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema F5BigIqAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'Password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'proxy_username',
                    'title': 'HTTPS Proxy User Name',
                    'type': 'string'
                },
                {
                    'name': 'proxy_password',
                    'title': 'HTTPS Proxy Password',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_f5_big_iq_reference_fields(raw_reference_info: dict):
        try:
            if not isinstance(raw_reference_info, dict):
                return None
            reference_info = ReferenceInfo()
            reference_info.id = raw_reference_info.get('id')
            reference_info.kind = raw_reference_info.get('kind')
            reference_info.link = raw_reference_info.get('link')
            reference_info.name = raw_reference_info.get('name')
            reference_info.partition = raw_reference_info.get('partition')
            return reference_info
        except Exception as e:
            logger.error(f'Error happened while filling reference info {raw_reference_info} fields: {str(e)}')
            return None

    @staticmethod
    def cidr_to_netmask(cidr):
        """
        convert cidr (<ip>/<netmask> string) to ip, subnet
        :return: ip, subnet tuple
        """
        if '/' not in cidr:
            return cidr, None
        network, net_bits = cidr.split('/')
        host_bits = 32 - int(net_bits)
        netmask = socket.inet_ntoa(struct.pack('!I', (1 << 32) - (1 << host_bits)))
        return network, netmask

    # pylint: disable=too-many-branches, too-many-statements
    def _fill_f5_big_iq_device_fields(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device.address_status = device_raw.get('addressStatus')
            device.auto_last_hop = device_raw.get('autoLasthop')
            device.connection_limit = int_or_none(device_raw.get('connectionLimit'))

            if isinstance(device_raw.get('defaultCookiePersistenceReference'), dict):
                device.default_cookie_persistence_reference = device_raw.get('defaultCookiePersistenceReference').get(
                    'link')

            if isinstance(device_raw.get('deviceReference'), dict):
                device_reference_raw = device_raw.get('deviceReference')
                device_reference = DeviceReference()
                device_reference.id = device_reference_raw.get('id')
                device_reference.kind = device_reference_raw.get('kind')
                device_reference.link = device_reference_raw.get('link')
                device_reference.machine_id = device_reference_raw.get('machineId')
                device_reference.name = device_reference_raw.get('name')
                device.device_reference = device_reference

            if isinstance(device_raw.get('fallbackSourceAddrPersistenceReference'), dict):
                device.fallback_source_addr_persistence_reference = device_raw.get(
                    'fallbackSourceAddrPersistenceReference').get('link')

            device.generation = int_or_none(device_raw.get('generation'))
            device.gtm_score = int_or_none(device_raw.get('gtmScore'))
            device.protocol = device_raw.get('ipProtocol')
            device.kind = device_raw.get('kind')
            device.mask = device_raw.get('mask')
            device.mirror = device_raw.get('mirror')
            device.nat64 = device_raw.get('nat64')
            device.partition = device_raw.get('partition')

            if isinstance(device_raw.get('poolReference'), dict):
                device.pool_reference = self._fill_f5_big_iq_reference_fields(device_raw.get('poolReference'))

            if isinstance(device_raw.get('profilesCollectionReference'), dict):
                profile_collection_reference_raw = device_raw.get('profilesCollectionReference')
                profile_collection_reference = ProfileCollectionReference()
                profile_collection_reference.link = profile_collection_reference_raw.get('link')
                profile_collection_reference.is_sub_collection = parse_bool_from_raw(
                    profile_collection_reference_raw.get('isSubcollection'))
                device.profile_collection_reference = profile_collection_reference

            device.rate_limit = device_raw.get('rateLimit')
            device.rate_limit_mode = device_raw.get('rateLimitMode')
            device.self_link = device_raw.get('selfLink')
            device.source_address = device_raw.get('sourceAddress')

            if isinstance(device_raw.get('sourceAddressTranslation'), dict):
                source_address_translation = device_raw.get('sourceAddressTranslation')
                source_address_translation_device = SourceAddressTranslation()
                source_address_translation_device.type = source_address_translation.get('type')
                source_address_translation_device.snat_pool_reference = self._fill_f5_big_iq_reference_fields(
                    source_address_translation.get('snatpoolReference'))
                device.source_address_translation = source_address_translation_device

            device.source_port = device_raw.get('sourcePort')
            device.state = device_raw.get('state')
            device.sub_path = device_raw.get('subPath')
            device.translate_port = device_raw.get('translatePort')
            if isinstance(device_raw.get('vlanReferences'), list):
                device.vlan_references = [vlan_refernce.get('link') for vlan_refernce in
                                          device_raw.get('vlanReferences') if
                                          isinstance(vlan_refernce, dict) and vlan_refernce.get('link')]
            device.vlans_enabled = device_raw.get('vlansEnabled')

            device.tunnel_references = []
            if isinstance(device_raw.get('tunnelReferences'), list):
                for tunnel_reference in device_raw.get('tunnelReferences'):
                    if not isinstance(tunnel_reference, dict):
                        continue
                    device.tunnel_references.append(self._fill_f5_big_iq_reference_fields(tunnel_reference))

            device.clone_pools = []
            if isinstance(device_raw.get('clonePools'), list):
                for clone_pool in device_raw.get('clonePools'):
                    if not isinstance(clone_pool, dict):
                        continue
                    clone_pool_device = ClonePool()
                    clone_pool_device.pool_reference = self._fill_f5_big_iq_reference_fields(
                        clone_pool.get('poolReference'))
                    clone_pool_device.context = clone_pool.get('context')
                    device.clone_pools.append(clone_pool_device)

            device.irule_references = []
            if isinstance(device_raw.get('iRuleReferences'), list):
                for irule_reference in device_raw.get('iRuleReferences'):
                    if not isinstance(irule_reference, dict):
                        continue
                    device.irule_references.append(self._fill_f5_big_iq_reference_fields(irule_reference))

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.description = device_raw.get('description')
            last_update_timestamp = int_or_none(device_raw.get('lastUpdateMicros'))
            if last_update_timestamp:
                # We need to divide it by 1000 because last_update_timestamp is in microseconds
                # and parse_date expects int of milliseconds.
                device.last_seen = parse_date(int(last_update_timestamp / 1000))
            device.name = device_raw.get('name')
            device.hostname = device_raw.get('name')

            subnets = device_raw.get('sourceAddress') or []
            ips = []
            if isinstance(subnets, str):
                try:
                    ips = [self.cidr_to_netmask(subnets)[0]]
                except Exception as e:
                    logger.warning(f'Couldn\'t parse ip from {subnets}: {str(e)}')
                subnets = [subnets]
            elif isinstance(subnets, list):
                try:
                    ips = [self.cidr_to_netmask(subnet)[0] for subnet in subnets if isinstance(subnet, str)]
                except Exception as e:
                    logger.warning(f'Couldn\'t parse ips from {subnets}: {str(e)}')
            device.add_nic(ips=ips, subnets=subnets)

            self._fill_f5_big_iq_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching F5BigIq Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching F5BigIq Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
