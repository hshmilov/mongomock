import datetime
import logging
import time

import requests

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.utils.parsing import parse_unix_timestamp
from rumble_adapter.connection import RumbleConnection
from rumble_adapter.client_id import get_client_id
from rumble_adapter.consts import DEFAULT_RUMBLE_DOMAIN, RUMBLE_AGENT_DOWNLOAD_LINK

logger = logging.getLogger(f'axonius.{__name__}')
RUMBLE_INSTALL_DONE_SUCCESS_MAGIC = 'RUMBLE_INSTALL_DONE_SUCCESSFULLY'


class RumbleRTT(SmartJsonClass):
    name = Field(str, 'Name')
    values = ListField(str, 'Values')


class RumbleKeyValue(SmartJsonClass):
    key = Field(str, 'Key')
    value = Field(str, 'Value')


class RumbleService(SmartJsonClass):
    service_address = Field(str, 'Service Address')
    service_port = Field(int, 'Service Port')
    service_transport = Field(str, 'Service Transport')


class RumbleAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        org_id = Field(str, 'Organization Id')
        org_name = Field(str, 'Organization Name')
        site_id = Field(str, 'Site Id')
        site_name = Field(str, 'Site Name')
        created_at = Field(datetime.datetime, 'Created At')
        updated_at = Field(datetime.datetime, 'Updated At')
        device_type = Field(str, 'Device Type')
        alive = Field(bool, 'Alive')
        detected_by = Field(str, 'Detected By')
        rumble_comments = Field(str, 'Comments')
        host_type = Field(str, 'Type')
        last_agent_id = Field(str, 'Last Agent Id')
        last_task_id = Field(str, 'Last Task Id')
        lowest_rtt = Field(int, 'Lowest RTT')
        lowest_ttl = Field(int, 'Lowest TTL')
        rumble_rtts = ListField(RumbleRTT, 'RTT')
        agent_name = Field(str, 'Agent Name')
        service_products = ListField(str, 'Service Products')
        service_protocols = ListField(str, 'Service Protocols')
        addresses_extra = ListField(str, 'Addresses Extra')
        rumble_domains = ListField(str, 'Domains')
        rumble_credentials = ListField(RumbleKeyValue, 'Rumble Credentials')
        rumble_services = ListField(RumbleService, 'Rumble Services')
        rumble_attributes = ListField(RumbleKeyValue, 'Rumble Attributes')
        arp_mac_vendor = Field(str, 'ARP MAC Vendor')
        nbns_mac_vendor = Field(str, 'NBNS MAC Vendor')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)
        self._agents = self._get_collection('rumble_agents')

    def install_agent_on_machine(self, download_token: str, proxy_string: str, just_check: bool = False):
        link = RUMBLE_AGENT_DOWNLOAD_LINK.format(download_token=download_token, epoch_time=int(time.time()))
        data = dict()
        proxies = None

        # Check if we have already installed
        if self._agents.find_one({'download_token': download_token}):
            logger.info(f'Agent already downloaded')
            return

        logger.info(f'Checking agent download...')
        if proxy_string:
            proxies = {'https': proxy_string}
            data['env'] = {'HTTPS_PROXY': proxy_string}

        # Make a stream mode to only get the status code as quickly as possible
        with requests.get(link, timeout=60, proxies=proxies, stream=True) as resp:
            try:
                resp.raise_for_status()
            except Exception as e:
                logger.exception(f'Exception: {str(e)} - status code {resp.status_code} content: {resp.text}')
                raise ValueError(f'Error - Can not validate download token')

        if just_check is True:
            return

        data['cmd'] = f'cd /home/ubuntu && curl -o rumble-agent.bin {link} && ' \
            f'chmod u+x rumble-agent.bin && ' \
            f'sudo ./rumble-agent.bin && rm -f rumble-agent.bin && echo {RUMBLE_INSTALL_DONE_SUCCESS_MAGIC}'

        current_instance_control_pun = self._get_adapter_unique_name('instance_control', self.node_id)

        logger.info(f'Installing Agent on {current_instance_control_pun}...')

        res = self._trigger_remote_plugin(
            current_instance_control_pun,
            job_name='execute_shell',
            data=data,
            timeout=300,
            stop_on_timeout=True
        )

        res.raise_for_status()
        res = res.text

        logger.info(f'Result from installation: {res}')
        if RUMBLE_INSTALL_DONE_SUCCESS_MAGIC in res:
            logger.info(f'Done installation successfully')
            self._agents.update_one(
                {'download_token': download_token},
                {
                    '$set': {
                        'download_token': download_token,
                        'time': datetime.datetime.now()
                    }
                },
                upsert=True
            )
        else:
            logger.critical(f'Error - could not install rumble agent')

        return

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain') or DEFAULT_RUMBLE_DOMAIN,
                                                https_proxy=client_config.get('https_proxy'))

    def get_connection(self, client_config):
        connection = RumbleConnection(domain=client_config.get('domain') or DEFAULT_RUMBLE_DOMAIN,
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      apikey=client_config['apikey'])
        with connection:
            pass

        download_token = client_config.get('download_token')
        if download_token:
            self.install_agent_on_machine(download_token, client_config.get('https_proxy'), just_check=True)
        return connection, client_config

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        client, client_config = client_data
        try:
            download_token = client_config.get('download_token')
            if download_token:
                self.install_agent_on_machine(download_token, client_config.get('https_proxy'))
        except Exception:
            logger.exception(f'Could not install agent on machine, continuing')

        with client:
            yield from client.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema RumbleAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Rumble Network Discovery Domain',
                    'type': 'string',
                    'default': DEFAULT_RUMBLE_DOMAIN
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'download_token',
                    'title': 'Download Token',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool',
                    'default': True
                },
            ],
            'required': [
                'domain',
                'apikey',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    @staticmethod
    def _create_device(device_raw, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + str((device_raw.get('names') or ''))
            if device_raw.get('names') and isinstance(device_raw.get('names'), list):
                hostname = device_raw.get('names')[0]
                if len(device_raw.get('names')) > 1 and device_raw.get('names')[1].split('.')[0] == hostname:
                    hostname = device_raw.get('names')[1]
                device.hostname = hostname
            device.add_ips_and_macs(ips=device_raw.get('addresses'), macs=device_raw.get('macs'))
            device.last_seen = parse_unix_timestamp(device_raw.get('last_seen'))
            device.first_seen = parse_unix_timestamp(device_raw.get('first_seen'))
            device.alive = bool(device_raw.get('alive'))
            device.site_id = device_raw.get('site_id')
            device.site_name = device_raw.get('site_name')
            device.created_at = parse_unix_timestamp(device_raw.get('created_at'))
            device.updated_at = parse_unix_timestamp(device_raw.get('updated_at'))
            device.org_id = device_raw.get('organization_id')
            device.org_name = device_raw.get('org_name')
            device.detected_by = device_raw.get('detected_by')
            device.agent_name = device_raw.get('Agent Name')
            device.rumble_comments = device_raw.get('comments')
            device.host_type = device_raw.get('type')
            device.last_agent_id = device_raw.get('last_agent_id')
            device.last_task_id = device_raw.get('last_task_id')
            device.lowest_rtt = device_raw.get('lowest_rtt') if isinstance(device_raw.get('lowest_rtt'), int) else None
            device.lowest_ttl = device_raw.get('lowest_ttl') if isinstance(device_raw.get('lowest_ttl'), int) else None
            device.device_model = device_raw.get('hw')

            for tcp_port in (device_raw.get('service_ports_tcp') or []):
                try:
                    port = int(tcp_port)
                    device.add_open_port('TCP', port)
                except Exception:
                    logger.exception(f'Problem adding TCP port {tcp_port}')

            for udp_port in (device_raw.get('service_ports_udp') or []):
                try:
                    port = int(udp_port)
                    device.add_open_port('UDP', port)
                except Exception:
                    logger.exception(f'Problem adding TCP port {udp_port}')

            try:
                device.service_products = device_raw.get('service_products') \
                    if isinstance(device_raw.get('service_products'), list) else None
            except Exception:
                logger.exception(f'Problem adding service products')

            try:
                device.service_protocols = device_raw.get('service_protocols') \
                    if isinstance(device_raw.get('service_protocols'), list) else None
            except Exception:
                logger.exception(f'Problem adding service products')

            try:
                device.figure_os((device_raw.get('os') or '') + ' ' + (device_raw.get('os_version') or ''))
            except Exception:
                logger.exception(f'Problem getting os for {device_raw}')

            try:
                rumble_attributes = (device_raw.get('attributes') or {})
                for key, value in rumble_attributes.items():
                    device.rumble_attributes.append(RumbleKeyValue(
                        key=key,
                        value=value
                    ))
            except Exception:
                logger.exception(f'Error parsing rumble attributes')

            try:
                rumble_credentials = (device_raw.get('credentials') or {})
                for key, value in rumble_credentials.items():
                    device.rumble_credentials.append(RumbleKeyValue(
                        key=key,
                        value=value
                    ))
            except Exception:
                logger.exception(f'Error parsing rumble credentials')

            try:
                rumble_services = (device_raw.get('services') or {})
                for rumble_service in rumble_services.values():
                    if rumble_service.get('source') == 'arp':
                        device.arp_mac_vendor = rumble_service.get('arp.macVendor')
                    if rumble_service.get('protocol') == 'netbios':
                        device.nbns_mac_vendor = rumble_service.get('netbios.macVendor')
                    service_address = rumble_service.get('service.address')
                    try:
                        service_port = int(rumble_service.get('service.port'))
                    except Exception:
                        service_port = None

                    service_transport = rumble_service.get('service.transport')

                    if service_address or service_port or service_transport:
                        device.rumble_services.append(
                            RumbleService(
                                service_address=service_address,
                                service_port=service_port,
                                service_transport=service_transport
                            )
                        )
            except Exception:
                logger.exception(f'Error parsing rumble services')

            try:
                addresses_extra = device_raw.get('addresses_extra')
                if addresses_extra and isinstance(addresses_extra, list):
                    device.addresses_extra = addresses_extra
            except Exception:
                logger.exception(f'Error parsing addresses extra')

            try:
                domains = device_raw.get('domains')
                if domains and isinstance(domains, list):
                    device.rumble_domains = domains
            except Exception:
                logger.exception(f'Error parsing domains')

            try:
                for tag_key, tag_value in (device_raw.get('tags') or {}).items():
                    device.add_key_value_tag(tag_key, tag_value)
            except Exception:
                logger.exception(f'Error adding tags')

            try:
                for rtt_name, rtt_values in (device_raw.get('rtts') or {}).items():
                    device.rumble_rtts.append(RumbleRTT(
                        name=rtt_name,
                        values=rtt_values
                    ))
            except Exception:
                logger.exception(f'Error adding RTTs')

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Rumble Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw, self._new_device_adapter())
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network]
