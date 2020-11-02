import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.vmware_vrops.connection import VmwareVropsConnection
from axonius.devices.device_adapter import DeviceRunningState
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none, float_or_none, is_valid_ip
from vmware_vrops_adapter.client_id import get_client_id
from vmware_vrops_adapter.structures import VmwareVropsDeviceInstance, ResourceKey, ResourceIdentifier, GeoLocation, \
    ResourceStatusState, Badge, Alert, RESOURCE_HEALTH, RESOURCE_STATUS_ENUM, RESOURCE_STATE_ENUM, BADGE_TYPE, \
    BADGE_COLOR, ALERT_LEVEL, ALERT_STATUS, CONTROL_STATE

logger = logging.getLogger(f'axonius.{__name__}')


def parse_enum(device_raw: dict, field_name: str, whitelist: list):
    value = device_raw.get(field_name)
    if value not in whitelist and value is not None:
        logger.warning(f'Unknown "{field_name}" value encountered {value}'
                       f' for whitelist {whitelist} in raw: {device_raw}.')
    return value


class VmwareVropsAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(VmwareVropsDeviceInstance):
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
        connection = VmwareVropsConnection(domain=client_config.get('domain'),
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

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list(ignore_not_existing_devices=self._ignore_not_existing_devices)

    @staticmethod
    def _clients_schema():
        """
        The schema VmwareVropsAdapter expects from configs

        :param **kwargs:
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

    # pylint: disable=too-many-branches, too-many-statements
    @staticmethod
    def _fill_vmware_vrops_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.credential_instance_id = device_raw.get('credentialInstanceId')
            device.resource_health = parse_enum(device_raw, 'resourceHealth', RESOURCE_HEALTH)
            device.resource_health_value = device_raw.get('resourceHealthValue')
            device.monitoring_interval = int_or_none(device_raw.get('monitoringInterval'))

            resource_key_raw = device_raw.get('resourceKey')
            if isinstance(resource_key_raw, dict):
                resource_key = ResourceKey()
                resource_key.name = resource_key_raw.get('name')
                resource_key.adapter_kind_key = resource_key_raw.get('adapterKindKey')
                resource_key.resource_kind_key = resource_key_raw.get('resourceKindKey')

                resource_identifiers_raw = resource_key_raw.get('resourceIdentifiers')

                resource_key.resource_identifiers = []
                if isinstance(resource_identifiers_raw, list):
                    for resource_identifier_raw in resource_identifiers_raw:
                        if not isinstance(resource_identifier_raw, dict):
                            continue

                        resource_identifier = ResourceIdentifier()
                        identifier_type_raw = resource_identifier_raw.get('identifierType')
                        resource_identifier.value = resource_identifier_raw.get('value')
                        if isinstance(identifier_type_raw, dict):
                            resource_identifier.name = identifier_type_raw.get('name')
                            resource_identifier.data_type = identifier_type_raw.get('dataType')
                            resource_identifier.is_part_of_uniqueness = parse_bool_from_raw(
                                identifier_type_raw.get('isPartOfUniqueness'))

                        if identifier_type_raw.get('name') == 'VMEntityInstanceUUID':
                            device.cloud_id = resource_identifier_raw.get('value')

                        resource_key.resource_identifiers.append(resource_identifier)

                device.resource_key = resource_key

            geo_location_raw = device_raw.get('geoLocation')
            if isinstance(geo_location_raw, dict):
                geo_location = GeoLocation()
                geo_location.latitude = float_or_none(geo_location_raw.get('latitude'))
                geo_location.longitude = float_or_none(geo_location_raw.get('longitude'))

                device.geo_location = geo_location

            device.resource_status_states = []
            resource_status_states_raw = device_raw.get('resourceStatusStates')
            if isinstance(resource_status_states_raw, list):
                for resource_status_state_raw in resource_status_states_raw:
                    if not isinstance(resource_status_state_raw, dict):
                        continue
                    resource_status_state = ResourceStatusState()
                    resource_status_state.adapter_instance_id = resource_status_state_raw.get('adapterInstanceId')
                    resource_status_state.resource_status = parse_enum(resource_status_state_raw, 'resourceStatus',
                                                                       RESOURCE_STATUS_ENUM)
                    resource_status_state.resource_state = parse_enum(resource_status_state_raw, 'resourceState',
                                                                      RESOURCE_STATE_ENUM)
                    resource_status_state.status_message = resource_status_state_raw.get('statusMessage')

                    device.resource_status_states.append(resource_status_state)

            device.badges = []
            badges_raw = device_raw.get('badges')
            if isinstance(badges_raw, list):
                for badge_raw in badges_raw:
                    if not isinstance(badge_raw, dict):
                        continue
                    badge = Badge()
                    badge.type = parse_enum(badge_raw, 'type', BADGE_TYPE)
                    badge.color = parse_enum(badge_raw, 'color', BADGE_COLOR)
                    badge.score = float_or_none(badge_raw.get('score'))

                    device.badges.append(badge)

            device.alerts = []
            alerts_raw = device_raw.get('extra_alerts')
            if isinstance(alerts_raw, list):
                for alert_raw in alerts_raw:
                    if not isinstance(alert_raw, dict):
                        continue
                    alert = Alert()
                    alert.alert_id = alert_raw.get('alertId')
                    alert.resource_id = alert_raw.get('resourceId')
                    alert.alert_level = parse_enum(alert_raw, 'alertLevel', ALERT_LEVEL)
                    alert.alert_type = alert_raw.get('type')
                    alert.sub_type = alert_raw.get('subType')
                    alert.status = parse_enum(alert_raw, 'status', ALERT_STATUS)
                    alert.start_time = parse_date(alert_raw.get('startTimeUTC'))
                    alert.cancel_time = parse_date(alert_raw.get('cancelTimeUTC'))
                    alert.update_time = parse_date(alert_raw.get('updateTimeUTC'))
                    alert.suspend_until_time = parse_date(alert_raw.get('suspendUntilTimeUTC'))
                    alert.control_state = parse_enum(alert_raw, 'controlState', CONTROL_STATE)
                    alert.stat_key = alert_raw.get('statKey')
                    alert.owner_id = alert_raw.get('ownerId')
                    alert.owner_name = alert_raw.get('ownerName')
                    alert.alert_definition_id = alert_raw.get('alertDefinitionId')
                    alert.alert_definition_name = alert_raw.get('alertDefinitionName')
                    alert.alert_impact = alert_raw.get('alertImpact')

                    device.alerts.append(alert)

            properties_raw = device_raw.get('extra_properties')
            if isinstance(properties_raw, dict):
                if isinstance(properties_raw.get('summary|config|productName'), list):
                    device.product_name = properties_raw.get('summary|config|productName')[0]
                else:
                    device.product_name = properties_raw.get('summary|config|productName')

                if isinstance(properties_raw.get('summary|customTag:SN_ConfigItemID|customTagValue'), list) and \
                        properties_raw.get('summary|customTag:SN_ConfigItemID|customTagValue'):
                    device.service_now_config_item_id = \
                        properties_raw.get('summary|customTag:SN_ConfigItemID|customTagValue')[0]
                else:
                    device.service_now_config_item_id = properties_raw.get(
                        'summary|customTag:SN_ConfigItemID|customTagValue')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('identifier')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None

            resource_key_raw = device_raw.get('resourceKey')
            device.id = str(device_id) + '_' + ((device_raw.get('resourceKey') or {}).get('name') or '')

            if isinstance(resource_key_raw, dict):
                device.name = resource_key_raw.get('name')
                device.hostname = resource_key_raw.get('name')

            device.first_seen = parse_date(device_raw.get('creationTime'))
            if parse_bool_from_raw(device_raw.get('dtEnabled')) is not None:
                device.device_disabled = not parse_bool_from_raw(device_raw.get('dtEnabled'))

            device.description = device_raw.get('description')

            properties_raw = device_raw.get('extra_properties')

            if isinstance(properties_raw, dict):
                if isinstance(properties_raw.get('config|hardware|memoryKB'), list):
                    if isinstance(properties_raw.get('config|hardware|memoryKB')[0], int):
                        device.total_physical_memory = (float_or_none(
                            properties_raw.get('config|hardware|memoryKB')[0]) or 0) / (1024 ** 3)  # From KB to GB
                    else:
                        device.total_physical_memory = (float_or_none(
                            properties_raw.get('config|hardware|memoryKB')[0]) or 0) / (1024 ** 3)  # From KB to GB
                elif isinstance(properties_raw.get('config|hardware|memoryKB'), int):
                    device.total_physical_memory = (float_or_none(
                        properties_raw.get('config|hardware|memoryKB')) or 0) / (1024 ** 3)  # From KB to GB
                else:
                    device.total_physical_memory = (float_or_none(
                        properties_raw.get('config|hardware|memoryKB')) or 0) / (1024 ** 3)  # From KB to GB

                if isinstance(properties_raw.get('summary|guest|hostName'), list):
                    device.hostname = properties_raw.get('summary|guest|hostName')[0]
                else:
                    device.hostname = properties_raw.get('summary|guest|hostName')

                if properties_raw.get('summary|guest|hostName') is None:
                    if isinstance(properties_raw.get('config|name'), list):
                        device.hostname = properties_raw.get('config|name')[0]
                    else:
                        device.hostname = properties_raw.get('config|name')

                if isinstance(properties_raw.get('config|guestFullName'), list):
                    device.figure_os(properties_raw.get('config|guestFullName')[0])
                elif properties_raw.get('config|guestFullName') is not None:
                    device.figure_os(properties_raw.get('config|guestFullName'))

                if properties_raw.get('config|guestFullName') is None:
                    if isinstance(properties_raw.get('sys|productString'), list):
                        product_name = properties_raw.get('sys|productString')[0]
                    else:
                        product_name = properties_raw.get('sys|productString')

                    if isinstance(properties_raw.get('summary|version'), list):
                        version = properties_raw.get('summary|version')[0]
                    else:
                        version = properties_raw.get('summary|version')

                    if product_name is not None and version is not None:
                        device.figure_os(f'{product_name}_{version}')
                    elif product_name is not None:
                        device.figure_os(product_name)
                    elif version is not None:
                        device.figure_os(version)

                    if isinstance(properties_raw.get('sys|build'), list):
                        device.os.build = properties_raw.get('sys|build')[0]
                    else:
                        device.os.build = properties_raw.get('sys|build')

                if isinstance(properties_raw.get('config|hardware|numCoresPerSocket'), list):
                    number_of_cores_per_socket = int_or_none(
                        properties_raw.get('config|hardware|numCoresPerSocket')[0]) or 0
                else:
                    number_of_cores_per_socket = int_or_none(
                        properties_raw.get('config|hardware|numCoresPerSocket')) or 0

                if isinstance(properties_raw.get('config|hardware|numSockets'), list):
                    number_of_sockets = int_or_none(properties_raw.get('config|hardware|numSockets')[0]) or 0
                else:
                    number_of_sockets = int_or_none(properties_raw.get('config|hardware|numSockets')) or 0

                device.total_number_of_cores = number_of_cores_per_socket * number_of_sockets

                if isinstance(properties_raw.get('hardware|cpuInfo|numCpuCores'), list) and \
                        not device.total_number_of_cores:
                    device.total_number_of_cores = int_or_none(properties_raw.get('hardware|cpuInfo|numCpuCores')[0])
                else:
                    device.total_number_of_cores = int_or_none(properties_raw.get('hardware|cpuInfo|numCpuCores'))

                if isinstance(properties_raw.get('summary|runtime|powerState'), list):
                    power_state_raw = properties_raw.get('summary|runtime|powerState')[0]
                else:
                    power_state_raw = properties_raw.get('summary|runtime|powerState')

                device.power_state = {'Powered On': DeviceRunningState.TurnedOn,
                                      'Powered Off': DeviceRunningState.TurnedOff}.get(power_state_raw)

                if isinstance(properties_raw.get('summary|guest|ipAddress'), list):
                    device.add_ips_and_macs(
                        ips=[ip for ip in properties_raw.get('summary|guest|ipAddress') if is_valid_ip(ip)])
                elif is_valid_ip(properties_raw.get('summary|guest|ipAddress')):
                    device.add_ips_and_macs(ips=[properties_raw.get('summary|guest|ipAddress')])

                if isinstance(properties_raw.get('net|ip_address'), list):
                    device.add_ips_and_macs(
                        ips=[ip for ip in properties_raw.get('net|ip_address') if is_valid_ip(ip)])
                elif is_valid_ip(properties_raw.get('net|ip_address')):
                    device.add_ips_and_macs(ips=[properties_raw.get('net|ip_address')])

                if isinstance(properties_raw.get('net|mgmt_address'), list):
                    device.add_ips_and_macs(
                        ips=[ip for ip in properties_raw.get('net|mgmt_address') if is_valid_ip(ip)])
                elif is_valid_ip(properties_raw.get('net|mgmt_address')):
                    device.add_ips_and_macs(ips=[properties_raw.get('net|mgmt_address')])

                if isinstance(properties_raw.get('config|hardware|diskSpace'), list):
                    device.add_hd(total_size=int_or_none(properties_raw.get('config|hardware|diskSpace')[0]))
                else:
                    device.add_hd(total_size=int_or_none(properties_raw.get('config|hardware|diskSpace')))

                if isinstance(properties_raw.get('config|hardware|numCpu'), list):
                    number_of_cpus = int_or_none(properties_raw.get('config|hardware|numCpu')[0])
                else:
                    number_of_cpus = int_or_none(properties_raw.get('config|hardware|numCpu'))

                if isinstance(properties_raw.get('cpu|cpuModel'), list):
                    cpu_model = properties_raw.get('cpu|cpuModel')[0]
                else:
                    cpu_model = properties_raw.get('cpu|cpuModel')

                device.add_cpu(cores=number_of_cpus, manufacturer=cpu_model)

                if isinstance(properties_raw.get('config|network|dnsserver'), list):
                    device.dns_servers = [properties_raw.get('config|network|dnsserver')[0]]
                elif properties_raw.get('config|network|dnsserver') is not None:
                    device.dns_servers = [properties_raw.get('config|network|dnsserver')]

                if isinstance(properties_raw.get('hardware|biosVersion'), list):
                    device.bios_version = properties_raw.get('hardware|biosVersion')[0]
                else:
                    device.bios_version = properties_raw.get('hardware|biosVersion')

                if isinstance(properties_raw.get('hardware|vendor'), list):
                    device.device_manufacturer = properties_raw.get('hardware|vendor')[0]
                else:
                    device.device_manufacturer = properties_raw.get('hardware|vendor')

                if isinstance(properties_raw.get('hardware|vendorModel'), list):
                    device.device_model = properties_raw.get('hardware|vendorModel')[0]
                else:
                    device.device_model = properties_raw.get('hardware|vendorModel')

                if isinstance(properties_raw.get('summary|hostuuid'), list):
                    device.cloud_id = properties_raw.get('summary|hostuuid')[0]
                else:
                    device.cloud_id = properties_raw.get('summary|hostuuid')

                for i in range(1000):  # Support only 1000 ips and mac to parse.
                    ips = []
                    ip_address = properties_raw.get(f'net:{4000 + i}|ip_address')
                    if ip_address and isinstance(ip_address, list):
                        ips = [ip_address[0]]
                    if isinstance(ip_address, str) and ',' in ip_address:
                        ips = [ip.strip() for ip in ip_address.split(',')
                               if ip.strip()]

                    if isinstance(properties_raw.get(f'net:{4000 + i}|mac_address'), list):
                        mac_address = properties_raw.get(f'net:{4000 + i}|mac_address')[0]
                    else:
                        mac_address = properties_raw.get(f'net:{4000 + i}|mac_address')

                    if not (ips or mac_address):
                        continue
                    device.add_nic(mac=mac_address, ips=ips)

                if isinstance(properties_raw.get('config|hardware|diskSpace'), list):
                    device.add_hd(total_size=float_or_none(
                        properties_raw.get('config|hardware|diskSpace')[0]))
                else:
                    device.add_hd(total_size=float_or_none(
                        properties_raw.get('config|hardware|diskSpace')))

                if isinstance(properties_raw.get('hardware|enclosureSerialNumberTag'), list) and \
                        properties_raw.get('hardware|enclosureSerialNumberTag'):
                    device.device_serial = properties_raw.get('hardware|enclosureSerialNumberTag')[0]
                else:
                    device.device_serial = properties_raw.get('hardware|enclosureSerialNumberTag')

                if device.get_field_safe('device_serial') is None and \
                        properties_raw.get('hardware|serialNumberTag'):
                    if isinstance(properties_raw.get('hardware|serialNumberTag'), list):
                        device.device_serial = properties_raw.get('hardware|serialNumberTag')[0]
                    else:
                        device.device_serial = properties_raw.get('hardware|serialNumberTag')

                if device.get_field_safe('device_serial') is None and \
                        properties_raw.get('hardware|serviceTag'):
                    if isinstance(properties_raw.get('hardware|serviceTag'), list):
                        device.device_serial = properties_raw.get('hardware|serviceTag')[0]
                    else:
                        device.device_serial = properties_raw.get('hardware|serviceTag')

            self._fill_vmware_vrops_device_fields(device_raw, device)
            device.cloud_provider = 'VMWare'
            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching VmwareVrops Device for {device_raw}')
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
                logger.exception(f'Problem with fetching VmwareVrops Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Virtualization]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'ignore_not_existing_devices',
                    'title': 'Ignore "NOT_EXISTING" devices',
                    'type': 'bool'
                }
            ],
            'required': [
                'ignore_not_existing_devices',
            ],
            'pretty_name': 'VMWare vROps Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'ignore_not_existing_devices': True,
        }

    def _on_config_update(self, config):
        self._ignore_not_existing_devices = parse_bool_from_raw(config.get('ignore_not_existing_devices'))
        if self._ignore_not_existing_devices is None:
            self._ignore_not_existing_devices = True
