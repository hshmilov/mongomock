import datetime
import ipaddress
import logging

from axonius.smart_json_class import SmartJsonClass
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.fields import Field, ListField
from axonius.utils.datetime import parse_date
from riskiq_adapter.connection import RiskiqConnection
from riskiq_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class WebsiteComponent(SmartJsonClass):
    type = Field(str, 'Type')
    name = Field(str, 'Name')
    version = Field(str, 'Version')
    name_ver = Field(str, 'Name Version')
    first_seen = Field(datetime.datetime, 'First Seen')
    last_seen = Field(datetime.datetime, 'Last Seen')
    affected = Field(bool, 'Affected by known CVE')


class SecpolRecord(SmartJsonClass):
    name = Field(str, 'Policy Name')
    first_clean = Field(datetime.datetime, 'First clean')
    last_clean = Field(datetime.datetime, 'Last clean')
    affected = Field(bool, 'Currently affected')
    last_affected = Field(datetime.datetime, 'Last affected')
    first_affected = Field(datetime.datetime, 'First affected')
    description = Field(str, 'Policy status description')


class IPBlock(SmartJsonClass):
    asset_id = Field(int, 'RiskIQ Asset ID')
    ip_block = Field(str, 'IP Block')
    ip_start = Field(str, 'IP Start')
    ip_end = Field(str, 'IP End')
    cidr = Field(int, 'CIDR')


class RiskiqAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        cname = Field(str, 'CName')
        host = Field(str, 'Host')
        full_host = Field(str, 'Full Host')
        workspace = Field(int, 'Workspace ID')
        asset_status = Field(str, 'Asset status')
        inventory_state = Field(str, 'Inventory State')
        detail_state = Field(str, 'Detail state')
        last_changed = Field(datetime.datetime, 'Last Changed')
        last_detailed = Field(datetime.datetime, 'Last Detailed')
        created_time = Field(datetime.datetime, 'Created at')
        updated_time = Field(datetime.datetime, 'Updated at')
        init_url = Field(str, 'Initial website URL')
        final_url = Field(str, 'Final website URL')
        https = Field(bool, 'HTTPS Enabled')
        final_https = Field(bool, 'HTTPS Enabled on final URL')
        parked_page = Field(bool, 'Parked page')
        blacklisted = Field(bool, 'Blacklisted')
        site_status = Field(str, 'Site Status')
        secpol = ListField(SecpolRecord, 'Security Policy records')
        web_components = ListField(WebsiteComponent, 'Website Asset Components')
        ip_block = Field(IPBlock, 'IP Block data')

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
        connection = RiskiqConnection(domain=client_config['domain'],
                                      verify_ssl=client_config['verify_ssl'],
                                      https_proxy=client_config.get('https_proxy'),
                                      username=client_config['apikey'],
                                      password=client_config['apisecret'])
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema RiskiqAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'RiskIQ Domain',
                    'default': 'https://ws.riskiq.net',
                    'type': 'string'
                },
                {
                    'name': 'apikey',
                    'title': 'API Key',
                    'type': 'string',
                },
                {
                    'name': 'apisecret',
                    'title': 'API Secret',
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
                }
            ],
            'required': [
                'domain',
                'apikey',
                'apisecret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=R0912,R0915
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('assetID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            host_info = device_raw.get('host')
            if not host_info:
                logger.warning(f'Bad device with no host information: {device_raw}')
                return None
            device.hostname = host_info.get('host')
            device.name = device_raw.get('name')
            domain_info = device_raw.get('domain')
            if domain_info and isinstance(domain_info, dict):
                device.domain = domain_info.get('domain')
                device.dns_servers = domain_info.get('nameServers')
            if host_info.get('ipAddress'):
                try:
                    test_ip = ipaddress.ip_address(host_info.get('ipAddress'))
                    if test_ip.is_private:
                        device.add_ips_and_macs(ips=[str(test_ip)])
                    else:
                        device.add_public_ip(str(test_ip))
                except Exception:
                    logger.warning(f'Failed to add IP for {device_raw}')
            device.first_seen = parse_date(device_raw.get('firstSeen'))
            # And now for the specific stuff
            try:
                device.cname = host_info.get('cname')
                device.host = host_info.get('host')
                device.full_host = host_info.get('fullHost')
                device.workspace = device_raw.get('workspaceID')
                asset_status = device_raw.get('status')
                if self.__asset_status_whitelist and asset_status not in self.__asset_status_whitelist:
                    return None
                device.asset_status = asset_status
                inventory_state = device_raw.get('inventoryState')
                if self.__inventory_state_whitelist and inventory_state not in self.__inventory_state_whitelist:
                    return None
                device.inventory_state = inventory_state
                device.detail_state = device_raw.get('detailState')
                device.last_changed = parse_date(device_raw.get('lastChanged'))
                device.last_detailed = parse_date(device_raw.get('lastDetailed'))
                device.created_time = parse_date(device_raw.get('createdAt'))
                device.updated_time = parse_date(device_raw.get('updatedAt'))
            except Exception as e:
                logger.exception(f'Failed to set some adapter specific properties for device. '
                                 f'The exception was: {str(e)}. '
                                 f'Device: {device_raw}')
            if isinstance(device_raw.get('webSite'), dict):
                try:
                    ws_data = device_raw.get('webSite')
                    device.init_url = ws_data.get('initialUrl')
                    device.final_url = ws_data.get('finalUrl')
                    device.https = ws_data.get('https')
                    device.final_https = ws_data.get('finalUrlHttps')
                    device.parked_page = ws_data.get('parkedPage')
                    device.blacklisted = ws_data.get('blacklisted')
                    device.site_status = ws_data.get('siteStatus')
                except Exception as e:
                    logger.exception(f'Failed to set some website properties for device. '
                                     f'The exception was: {str(e)}. '
                                     f'website data: {ws_data}')
                if isinstance(ws_data.get('securityPolicyRecords'), list):
                    for secpol in ws_data.get('securityPolicyRecords'):
                        if not isinstance(secpol, dict):
                            continue
                        try:
                            device.secpol.append(SecpolRecord(
                                name=secpol.get('policyName'),
                                first_clean=parse_date(secpol.get('firstClean')),
                                last_clean=parse_date(secpol.get('lastClean')),
                                affected=secpol.get('currentlyAffected'),
                                description=secpol.get('description'),
                                last_affected=parse_date(secpol.get('lastAffected')),
                                first_affected=parse_date(secpol.get('firstAffected'))
                            ))
                        except Exception as e:
                            logger.exception(f'Failed to set device security policy. '
                                             f'The exception was: {str(e)}. '
                                             f'secpol data: {secpol}')
                if isinstance(ws_data.get('webSiteAssetWebComponents'), list):
                    for wc_data in ws_data.get('webSiteAssetWebComponents'):
                        if not isinstance(wc_data, dict):
                            continue
                        wc = wc_data.get('webComponent')
                        if not isinstance(wc, dict):
                            continue
                        try:
                            device.web_components.append(WebsiteComponent(
                                type=wc.get('type'),
                                name=wc.get('name'),
                                version=wc.get('version'),
                                name_ver=wc.get('nameVersion'),
                                last_seen=parse_date(wc_data.get('lastSeen')),
                                first_seen=parse_date(wc_data.get('firstSeen')),
                                affected=wc_data.get('affected')
                            ))
                        except Exception as e:
                            logger.exception(f'Failed to set device web component. '
                                             f'The exception was: {str(e)}. '
                                             f'web component data: {wc}')
            # Yeah, that's a lot of stuff to do if it's got ws_data
            try:
                if isinstance(device_raw.get('ipBlock'), dict):
                    ib_data = device_raw.get('ipBlock')
                    device.ip_block = IPBlock(
                        asset_id=ib_data.get('assetID'),
                        ip_block=ib_data.get('ipBlock'),
                        ip_start=ib_data.get('ipStart'),
                        ip_end=ib_data.get('ipEnd'),
                        cidr=ib_data.get('cidr')
                    )
            except Exception as e:
                message = f'Failed to set ip_block for device. Reason: {str(e)}. ' \
                          f'Device information: {device_raw}'
                logger.exception(message)
            # Aaaaand that's that
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Riskiq Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'inventory_state_whitelist',
                    'title': 'Inventory State Whitelist',
                    'type': 'string'
                },
                {
                    'name': 'asset_status_whitelist',
                    'title': 'Asset Status Whitelist',
                    'type': 'string'
                }
            ],
            'required': [
            ],
            'pretty_name': 'RiskIQ Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'asset_status_whitelist': None,
            'inventory_state_whitelist': None
        }

    def _on_config_update(self, config):
        self.__asset_status_whitelist = config.get('asset_status_whitelist').split(',') \
            if config.get('asset_status_whitelist') else None
        self.__inventory_state_whitelist = config.get('inventory_state_whitelist').split(',') \
            if config.get('inventory_state_whitelist') else None
