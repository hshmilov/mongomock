import ipaddress
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.mixins.configurable import Configurable
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import parse_bool_from_raw
from riskiq_adapter.connection import RiskiqConnection
from riskiq_adapter.client_id import get_client_id
from riskiq_adapter.consts import RISKIQ_API_URL_DEFAULT
from riskiq_adapter.structures import RiskIqDeviceInstance, WebsiteComponent, RiskIqOrganization, \
    RiskIqBrand, RiskIqTag

logger = logging.getLogger(f'axonius.{__name__}')


class RiskiqAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(RiskIqDeviceInstance):
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
                    'default': RISKIQ_API_URL_DEFAULT,
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

    # pylint: disable=too-many-branches, too-many-statements, invalid-triple-quote
    @staticmethod
    def _fill_riskiq_device_fields(device: RiskIqDeviceInstance, device_raw: dict):
        """ Parse the raw information, first the stuff that's generic to all RiskIQ asset types,
        and then the stuff that is specific to HOST_ASSET .
        The order allows the best chance to parse the most information.
        """  # XXX What's up with pylint suddenly not liking my docstrings?
        device.updated_time = parse_date(device_raw.get('updatedAt'))
        device.created_time = parse_date(device_raw.get('createdAt'))
        device.inventory_state = device_raw.get('state')
        device.external_id = device_raw.get('externalID')
        device.device_type = device_raw.get('type')
        device.is_auto_confirm = parse_bool_from_raw(device_raw.get('autoConfirmed'))
        device.is_enterprise = parse_bool_from_raw(device_raw.get('enterprise'))
        device.confidence = device_raw.get('confidence')
        device.priority = device_raw.get('priority')
        device.removed_state = device_raw.get('removedState')
        device.riskiq_label = device_raw.get('label')
        device.is_keystone = parse_bool_from_raw(device_raw.get('keystone'))
        device.external_metadata = device_raw.get('externalMetadata')

        # organizations
        orgs_raw = device_raw.get('organizations')
        if orgs_raw and isinstance(orgs_raw, list):
            for org_raw in orgs_raw:
                if not isinstance(org_raw, dict):
                    continue
                try:
                    org = RiskIqOrganization(
                        workspace_id=org_raw.get('workspaceID'),
                        workspace_org_id=org_raw.get('workspaceOrganizationID'),
                        status=org_raw.get('status'),
                        name=org_raw.get('name'),
                        org_id=org_raw.get('id'),
                        created=parse_date(org_raw.get('createdAt')),
                        updated=parse_date(org_raw.get('updatedAt'))
                    )
                    device.orgs.append(org)
                except Exception as e:
                    logger.debug(f'Error parsing org {org_raw}: {str(e)}')

        # brands
        brands_raw = device_raw.get('brands')
        if brands_raw and isinstance(brands_raw, list):
            for brand_raw in brands_raw:
                if not isinstance(brand_raw, dict):
                    continue
                try:
                    brand = RiskIqBrand(
                        workspace_id=brand_raw.get('workspaceID'),
                        workspace_brand_id=brand_raw.get('workspaceBrandID'),
                        status=brand_raw.get('status'),
                        name=brand_raw.get('name'),
                        brand_id=brand_raw.get('id'),
                        created=parse_date(brand_raw.get('createdAt')),
                        updated=parse_date(brand_raw.get('updatedAt'))
                    )
                    device.brands.append(brand)
                except Exception as e:
                    logger.debug(f'Error parsing brand {brand_raw}: {str(e)}')

        # tags
        tags_raw = device_raw.get('tags')
        if tags_raw and isinstance(tags_raw, list):
            for tag_raw in tags_raw:
                if not isinstance(tag_raw, dict):
                    continue
                try:
                    tag = RiskIqTag(
                        workspace_id=tag_raw.get('workspaceID'),
                        workspace_tag_id=tag_raw.get('workspaceTagID'),
                        workspace_tag_type=tag_raw.get('workspaceTagType'),
                        status=tag_raw.get('status'),
                        name=tag_raw.get('name'),
                        tag_id=tag_raw.get('id'),
                        created=parse_date(tag_raw.get('createdAt')),
                        updated=parse_date(tag_raw.get('updatedAt')),
                        tag_color=tag_raw.get('color')
                    )
                    device.tags.append(tag)
                except Exception as e:
                    logger.debug(f'Error parsing tag {tag_raw}: {str(e)}')

        # HOST_ASSET specific stuff
        asset_raw = device_raw.get('asset')  # Everything after this line relies on this dict
        if not (asset_raw and isinstance(asset_raw, dict)):  # Meaningless to continue if asset dict invalid or empty
            logger.warning(f'Invalid asset dict: Got {type(asset_raw)}')
            return

        device.host = asset_raw.get('host')
        device.alexa_rank = asset_raw.get('alexaRank')

        # web components
        wc_data = asset_raw.get('webComponents')
        if wc_data and isinstance(wc_data, list):
            for web_component in wc_data:
                if not isinstance(web_component, dict):
                    continue
                try:
                    component = WebsiteComponent(
                        category=web_component.get('webComponentCategory'),
                        name=web_component.get('webComponentName'),
                        version=web_component.get('webComponentVersion'),
                        affected=bool(web_component.get('cves')),  # Do not parse the cves, only whether they exist
                        last_seen=parse_date(web_component.get('lastSeen')),
                        first_seen=parse_date(web_component.get('firstSeen'))
                    )
                    if web_component.get('ruleid') and isinstance(web_component.get('ruleid'), list):
                        component.rule_ids = web_component.get('ruleid')
                    device.web_components.append(component)
                except Exception as e:
                    logger.debug(f'Failed to parse web component {web_component}: {str(e)}')

    # pylint: disable=R0912,R0915
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('uuid') or '')
            # Basics
            device.last_seen = parse_date(device_raw.get('lastSeen'))
            device.first_seen = parse_date(device_raw.get('firstSeen'))
            device.description = device_raw.get('description')
            device.name = device_raw.get('name')
            device.uuid = device_raw.get('uuid')
            # Whitelist
            inventory_state = device_raw.get('state')
            if self.__inventory_state_whitelist and inventory_state not in self.__inventory_state_whitelist:
                return None
            # Complex stuff
            host_info = device_raw.get('asset')
            if not (host_info and isinstance(host_info, dict)):
                logger.warning(f'Bad device with no host information: {device_raw}')
                return None
            device.hostname = host_info.get('host')

            # domain stuff
            domain_info = host_info.get('domainAsset')
            if domain_info and isinstance(domain_info, dict):
                device.domain = domain_info.get('domain')
                try:
                    device.dns_servers = domain_info.get('nameServers')
                except Exception as e:
                    logger.debug(f'Failed to parse name servers: {str(e)}')

            # ips
            ips_info = host_info.get('ipAddresses')
            if ips_info and isinstance(ips_info, list):
                for ip_info in ips_info:
                    if not isinstance(ip_info, dict):
                        continue
                    test_ip = ip_info.get('value')
                    try:
                        test_ip = ipaddress.ip_address(test_ip)
                        if test_ip.is_private:
                            device.add_ips_and_macs(ips=[str(test_ip)])
                        else:
                            device.add_public_ip(str(test_ip))
                    except Exception as e:
                        logger.warning(f'Error {str(e)} adding IP {test_ip} for {device_raw}')

            # Adapter-specific stuff
            try:
                self._fill_riskiq_device_fields(device, device_raw)
            except Exception as e:
                logger.exception(f'Failed to parse device specific fields for {device_raw}')

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
                    'title': 'Inventory state whitelist',
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
            'inventory_state_whitelist': None
        }

    def _on_config_update(self, config):
        self.__inventory_state_whitelist = config.get('inventory_state_whitelist').split(',') \
            if config.get('inventory_state_whitelist') else None
