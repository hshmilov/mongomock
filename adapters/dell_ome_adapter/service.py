import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.dell_ome.connection import DellOmeConnection
from axonius.clients.dell_ome.consts import EXTRA_INVENTORY, DEFAULT_ASYNC_CHUNKS_SIZE
from axonius.mixins.configurable import Configurable
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from dell_ome_adapter.client_id import get_client_id
from dell_ome_adapter.structures import DellOmeDeviceInstance, ServerCard, ServerProcessor, HostName, ArrayDisk, \
    RaidControl, MemoryDevice, PowerState, DeviceLicense, DeviceCapability, DeviceFru, DeviceLocation, DeviceSoftware, \
    SubSystemRollupStatus

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=logging-format-interpolation


class DellOmeAdapter(AdapterBase, Configurable):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DellOmeDeviceInstance):
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
        connection = DellOmeConnection(domain=client_config.get('domain'),
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
            yield from client_data.get_device_list(
                async_chunks=self.__async_chunks
            )

    @staticmethod
    def _clients_schema():
        """
        The schema DellOmeAdapter expects from configs

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
    def _fill_dell_ome_server_cards(server_cards_list: list, device: MyDeviceAdapter):
        try:
            server_cards = []
            for server_card_raw in server_cards_list:
                if isinstance(server_card_raw, dict):
                    server_card = ServerCard()
                    server_card.id = int_or_none(server_card_raw.get('Id'))
                    server_card.slot_number = server_card_raw.get('SlotNumber')
                    server_card.manufacturer = server_card_raw.get('Manufacturer')
                    server_card.description = server_card_raw.get('Description')
                    server_card.databus_width = server_card_raw.get('DatabusWidth')
                    server_card.slot_length = server_card_raw.get('SlotLength')
                    server_card.slot_type = server_card_raw.get('SlotType')
                    server_cards.append(server_card)

            device.server_cards = server_cards
        except Exception:
            logger.exception(f'Failed creating server card instance for device {server_cards_list}')

    @staticmethod
    def _fill_dell_ome_server_processors(server_processors_list: list, device: MyDeviceAdapter):
        try:
            server_processors = []
            for server_processor_raw in server_processors_list:
                if isinstance(server_processor_raw, dict):
                    server_processor = ServerProcessor()

                    name = server_processor_raw.get('BrandName')
                    family = server_processor_raw.get('Family')
                    cores = int_or_none(server_processor_raw.get('NumberOfCores'))

                    server_processor.id = int_or_none(server_processor_raw.get('Id'))
                    server_processor.family = family
                    server_processor.max_speed = int_or_none(server_processor_raw.get('MaxSpeed'))
                    server_processor.current_speed = int_or_none(server_processor_raw.get('CurrentSpeed'))
                    server_processor.slot_number = server_processor_raw.get('SlotNumber')
                    server_processor.status = int_or_none(server_processor_raw.get('Status'))
                    server_processor.number_of_cores = cores
                    server_processor.number_of_enabled_cores = int_or_none(
                        server_processor_raw.get('NumberOfEnabledCores'))
                    server_processor.brand_name = name
                    server_processor.model_name = server_processor_raw.get('ModelName')
                    server_processor.instance_id = server_processor_raw.get('InstanceId')
                    server_processor.voltage = server_processor_raw.get('Voltage')
                    server_processors.append(server_processor)

                    # Add aggregated data
                    device.add_cpu(name=name,
                                   family=family,
                                   cores=cores)

            device.server_processors = server_processors
        except Exception:
            logger.exception(f'Failed creating server processor instance for device {server_processors_list}')

    @staticmethod
    def _fill_dell_ome_operating_systems(operating_systems_list: list, device: MyDeviceAdapter):
        try:
            hostname = []
            server_host_names = []
            for server_operating_system_raw in operating_systems_list:
                if isinstance(server_operating_system_raw, dict):
                    host_name = HostName()
                    host_name.id = int_or_none(server_operating_system_raw.get('Id'))
                    host_name.host_name = server_operating_system_raw.get('Hostname')
                    hostname.append(server_operating_system_raw.get('Hostname'))
                    server_host_names.append(host_name)
            device.server_host_names = server_host_names

            if hostname:
                device.hostname = hostname[0]

        except Exception:
            logger.exception(f'Failed creating server operating systems for device {operating_systems_list}')

    @staticmethod
    def _fill_dell_ome_server_array_disks(server_array_disks_list: list, device: MyDeviceAdapter):
        try:
            serial_numbers = []
            server_array_disks = []
            for server_array_disk_raw in server_array_disks_list:
                if isinstance(server_array_disk_raw, dict):
                    server_array_disk = ArrayDisk()
                    server_array_disk.id = int_or_none(server_array_disk_raw.get('Id'))
                    server_array_disk.device_id = int_or_none(server_array_disk_raw.get('DeviceId'))
                    server_array_disk.disk_number = server_array_disk_raw.get('DiskNumber')
                    server_array_disk.vendor_name = server_array_disk_raw.get('VendorName')
                    server_array_disk.status = int_or_none(server_array_disk_raw.get('Status'))
                    server_array_disk.status_string = server_array_disk_raw.get('StatusString')
                    server_array_disk.model_number = server_array_disk_raw.get('ModelNumber')
                    server_array_disk.serial_number = server_array_disk_raw.get('SerialNumber')
                    serial_numbers.append(server_array_disk_raw.get('SerialNumber'))
                    server_array_disk.revision = server_array_disk_raw.get('Revision')
                    server_array_disk.enclosure_id = server_array_disk_raw.get('EnclosureId')
                    server_array_disk.channel = int_or_none(server_array_disk_raw.get('Channel'))
                    server_array_disk.size = server_array_disk_raw.get('Size')
                    server_array_disk.free_space = server_array_disk_raw.get('FreeSpace')
                    server_array_disk.used_space = server_array_disk_raw.get('UsedSpace')
                    server_array_disk.bus_type = server_array_disk_raw.get('BusType')
                    server_array_disk.slot_number = int_or_none(server_array_disk_raw.get('SlotNumber'))
                    server_array_disk.media_type = server_array_disk_raw.get('MediaType')
                    server_array_disk.remaining_read_write_endurance = server_array_disk_raw.get(
                        'RemainingReadWriteEndurance')
                    server_array_disk.security_state = server_array_disk_raw.get('SecurityState')
                    server_array_disks.append(server_array_disk)
            device.server_array_disks = server_array_disks

            if serial_numbers:
                device.device_serial = serial_numbers[0]

        except Exception:
            logger.exception(f'Failed creating server array disk instance for device {server_array_disks_list}')

    @staticmethod
    def _fill_dell_ome_server_raid_controls(server_raid_controls_list: list, device: MyDeviceAdapter):
        try:
            server_raid_controls = []
            for server_raid_control_raw in server_raid_controls_list:
                if isinstance(server_raid_control_raw, dict):
                    server_raid_control = RaidControl()
                    server_raid_control.id = int_or_none(server_raid_control_raw.get('Id'))
                    server_raid_control.device_id = int_or_none(server_raid_control_raw.get('DeviceId'))
                    server_raid_control.name = server_raid_control_raw.get('Name')
                    server_raid_control.fqdd = server_raid_control_raw.get('Fqdd')
                    server_raid_control.status = int_or_none(server_raid_control_raw.get('Status'))
                    server_raid_control.status_type_string = server_raid_control_raw.get('StatusTypeString')
                    server_raid_control.rollup_status = int_or_none(server_raid_control_raw.get('RollupStatus'))
                    server_raid_control.rollup_status_string = server_raid_control_raw.get('RollupStatusString')
                    server_raid_control.cache_size_mb = int_or_none(server_raid_control_raw.get('CacheSizeInMb'))
                    server_raid_control.pci_slot = int_or_none(server_raid_control_raw.get('PciSlot'))
                    server_raid_controls.append(server_raid_control)
            device.server_raid_controls = server_raid_controls
        except Exception:
            logger.exception(f'Failed creating server raid controls instance for device {server_raid_controls_list}')

    @staticmethod
    def _fill_dell_ome_server_memory_devices(server_memory_devices_list: list, device: MyDeviceAdapter):
        try:
            server_memory_devices = []
            for server_memory_device_raw in server_memory_devices_list:
                if isinstance(server_memory_device_raw, dict):
                    server_memory_device = MemoryDevice()
                    server_memory_device.id = int_or_none(server_memory_device_raw.get('Id'))
                    server_memory_device.name = server_memory_device_raw.get('Name')
                    server_memory_device.bank_name = server_memory_device_raw.get('BankName')
                    server_memory_device.size = int_or_none(server_memory_device_raw.get('Size'))
                    server_memory_device.status = int_or_none(server_memory_device_raw.get('Status'))
                    server_memory_device.manufacturer = server_memory_device_raw.get('Manufacturer')
                    server_memory_device.part_number = server_memory_device_raw.get('PartNumber')
                    server_memory_device.serial_number = server_memory_device_raw.get('SerialNumber')
                    server_memory_device.type_details = server_memory_device_raw.get('TypeDetails')
                    server_memory_device.manufacturer_date = parse_date(
                        server_memory_device_raw.get('ManufacturerDate'))
                    server_memory_device.speed = int_or_none(server_memory_device_raw.get('Speed'))
                    server_memory_device.current_operating_speed = int_or_none(
                        server_memory_device_raw.get('CurrentOperatingSpeed'))
                    server_memory_device.rank = server_memory_device_raw.get('Rank')
                    server_memory_device.instance_id = server_memory_device_raw.get('InstanceId')
                    server_memory_device.device_description = server_memory_device_raw.get('DeviceDescription')
                    server_memory_devices.append(server_memory_device)
            device.server_memory_devices = server_memory_devices
        except Exception:
            logger.exception(f'Failed creating server memory devices instance for device {server_memory_devices_list}')

    @staticmethod
    def _fill_dell_ome_server_power_states(server_power_states_list: list, device: MyDeviceAdapter):
        try:
            server_power_states = []
            for server_power_state_raw in server_power_states_list:
                if isinstance(server_power_state_raw, dict):
                    server_power_state = PowerState()
                    server_power_state.id = int_or_none(server_power_state_raw.get('Id'))
                    server_power_state.power_state = int_or_none(server_power_state_raw.get('PowerState'))
                    server_power_states.append(server_power_state)
            device.server_power_states = server_power_states
        except Exception:
            logger.exception(f'Failed creating server power states instance for device {server_power_states_list}')

    @staticmethod
    def _fill_dell_ome_device_licenses(device_licenses_list: list, device: MyDeviceAdapter):
        try:
            device_licenses = []
            for device_license_raw in device_licenses_list:
                if isinstance(device_license_raw, dict):
                    device_license = DeviceLicense()
                    device_license.sold_date = parse_date(device_license_raw.get('SoldDate'))
                    device_license.license_bound = int_or_none(device_license_raw.get('LicenseBound'))
                    device_license.eval_time_remaining = int_or_none(device_license_raw.get('EvalTimeRemaining'))
                    device_license.assigned_devices = device_license_raw.get('AssignedDevices')
                    device_license.license_status = int_or_none(device_license_raw.get('LicenseStatus'))
                    device_license.entitlement_id = device_license_raw.get('EntitlementId')
                    device_license.license_description = device_license_raw.get('LicenseDescription')

                    if isinstance(device_license_raw.get('LicenseType'), dict):
                        license_type_raw = device_license_raw.get('LicenseType')
                        device_license.license_type_name = license_type_raw.get('Name')
                        device_license.license_type_id = int_or_none(license_type_raw.get('LicenseId'))

                    device_licenses.append(device_license)
            device.device_licenses = device_licenses
        except Exception:
            logger.exception(f'Failed creating device licences instance for device {device_licenses_list}')

    @staticmethod
    def _fill_dell_ome_device_capabilities(device_capabilities_list: list, device: MyDeviceAdapter):
        try:
            device_capabilities = []
            for device_capability_raw in device_capabilities_list:
                if isinstance(device_capability_raw, dict):
                    device_capability = DeviceCapability()
                    device_capability.id = int_or_none(device_capability_raw.get('Id'))

                    if isinstance(device_capability_raw.get('CapabilityType'), dict):
                        capability_type_raw = device_capability_raw.get('CapabilityType')
                        device_capability.capability_id = int_or_none(capability_type_raw.get('CapabilityId'))
                        device_capability.capability_name = capability_type_raw.get('Name')
                        device_capability.capability_description = capability_type_raw.get('Description')

                    device_capabilities.append(device_capability)
            device.device_capabilities = device_capabilities
        except Exception:
            logger.exception(f'Failed creating device capabilities instance for device {device_capabilities_list}')

    @staticmethod
    def _fill_dell_ome_device_fru(device_fru_list: list, device: MyDeviceAdapter):
        try:
            device_fru = []
            for device_fru_raw in device_fru_list:
                if isinstance(device_fru_raw, dict):
                    fru = DeviceFru()
                    fru.id = int_or_none(device_fru_raw.get('Id'))
                    fru.manufacturer = device_fru_raw.get('Manufacturer')
                    fru.name = device_fru_raw.get('Name')
                    fru.part_number = device_fru_raw.get('PartNumber')
                    fru.serial_number = device_fru_raw.get('SerialNumber')
                    device_fru.append(fru)
            device.device_fru = device_fru
        except Exception:
            logger.exception(f'Failed creating device fru instance for device {device_fru_list}')

    @staticmethod
    def _fill_dell_ome_device_location(device_location_list: list, device: MyDeviceAdapter):
        try:
            device_location = []
            for device_location_raw in device_location_list:
                if isinstance(device_location_raw, dict):
                    location = DeviceLocation()
                    location.id = int_or_none(device_location_raw.get('Id'))
                    location.rack = device_location_raw.get('Rack')
                    location.aisle = device_location_raw.get('Aisle')
                    location.data_center = device_location_raw.get('Datacenter')
                    device_location.append(location)
            device.device_location = device_location
        except Exception:
            logger.exception(f'Failed creating device location instance for device {device_location_list}')

    @staticmethod
    def _fill_dell_ome_device_management(device_management_list: list, device: MyDeviceAdapter):
        try:
            for device_management_raw in device_management_list:
                if isinstance(device_management_raw, dict):
                    name = None
                    ips = device_management_raw.get('IpAddress') or []
                    if isinstance(ips, str):
                        ips = [ips]
                    if isinstance(device_management_raw.get('ManagementType'), dict):
                        name = device_management_raw.get('ManagementType').get('Name')

                    device.add_nic(mac=device_management_raw.get('MacAddress'),
                                   ips=ips,
                                   name=name)
            device.add_nic()
        except Exception:
            logger.exception(f'Failed adding device management for device {device_management_list}')

    @staticmethod
    def _fill_dell_ome_device_softwares(device_softwares_list: list, device: MyDeviceAdapter):
        try:
            device_softwares = []
            for device_software_raw in device_softwares_list:
                if isinstance(device_software_raw, dict):
                    device_software = DeviceSoftware()
                    device_software.version = device_software_raw.get('Version')
                    device_software.installation_date = parse_date(device_software_raw.get('InstallationDate'))
                    device_software.status = device_software_raw.get('Status')
                    device_software.software_type = device_software_raw.get('SoftwareType')
                    device_software.component_id = device_software_raw.get('ComponentId')
                    device_software.device_description = device_software_raw.get('DeviceDescription')
                    device_software.instance_id = device_software_raw.get('InstanceId')
                    device_softwares.append(device_software)

            device.device_softwares = device_softwares
        except Exception:
            logger.exception(f'Failed creating device softwares instance for device {device_softwares_list}')

    @staticmethod
    def _fill_dell_ome_device_rollup_status(system_rollup_status_list: list, device: MyDeviceAdapter):
        try:
            sub_system_rollup_status = []
            for status_raw in system_rollup_status_list:
                if isinstance(status_raw, dict):
                    status = SubSystemRollupStatus()
                    status.id = int_or_none(status_raw.get('Id'))
                    status.status = int_or_none(status_raw.get('Status'))
                    status.name = status_raw.get('SubsystemName')
                    sub_system_rollup_status.append(status)
            device.sub_system_rollup_status = sub_system_rollup_status
        except Exception:
            logger.exception(
                f'Failed creating device system rollup status instance for device {system_rollup_status_list}')

    def _fill_dell_ome_device_inventory_fields(self, device_inventory: list, device: MyDeviceAdapter):
        try:
            functions_by_inventory_type = {
                'ServerDeviceCards': self._fill_dell_ome_server_cards,
                'serverProcessors': self._fill_dell_ome_server_processors,
                'serverOperatingSystems': self._fill_dell_ome_operating_systems,
                'serverArrayDisks': self._fill_dell_ome_server_array_disks,
                'serverRaidControllers': self._fill_dell_ome_server_raid_controls,
                'serverMemoryDevices': self._fill_dell_ome_server_memory_devices,
                'serverSupportedPowerStates': self._fill_dell_ome_server_power_states,
                'deviceLicense': self._fill_dell_ome_device_licenses,
                'deviceCapabilities': self._fill_dell_ome_device_capabilities,
                'deviceFru': self._fill_dell_ome_device_fru,
                'deviceLocation': self._fill_dell_ome_device_location,
                'deviceManagement': self._fill_dell_ome_device_management,
                'deviceSoftware': self._fill_dell_ome_device_softwares,
                'subsystemRollupStatus': self._fill_dell_ome_device_rollup_status
            }

            for device_inventory_raw in device_inventory:
                if not (isinstance(device_inventory_raw, dict) and
                        isinstance(device_inventory_raw.get('InventoryInfo'), list)):
                    continue

                inventory_type = device_inventory_raw.get('InventoryType')
                device_inventory_list_info = device_inventory_raw.get('InventoryInfo')

                if functions_by_inventory_type.get(inventory_type):
                    functions_by_inventory_type[inventory_type](device_inventory_list_info, device)

        except Exception:
            logger.exception(f'Failed creating inventory instance for device {device_inventory}')

    @staticmethod
    def _fill_dell_ome_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.device_type = int_or_none(device_raw.get('Type'))
            device.identifier = device_raw.get('Identifier')
            device.chassis_service_tag = device_raw.get('ChassisServiceTag')
            device.state = int_or_none(device_raw.get('PowerState'))
            device.managed_state = int_or_none(device_raw.get('ManagedState'))
            device.status = int_or_none(device_raw.get('Status'))
            device.connection_status = parse_bool_from_raw(device_raw.get('ConnectionStatus'))
            device.asset_tag = device_raw.get('AssetTag')
            device.system_id = int_or_none(device_raw.get('SystemId'))

            try:
                if isinstance(device_raw.get('DeviceCapabilities'), list):
                    device.capabilities = device_raw.get('DeviceCapabilities')
            except Exception:
                logger.debug(f'Failed parsing device capabilities for {device_raw}')

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('Id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('DeviceName') or '')

            device.name = device_raw.get('DeviceName')
            device.device_model = device_raw.get('Model')

            last_inventory_time = parse_date(device_raw.get('LastInventoryTime'))
            last_status_time = parse_date(device_raw.get('LastStatusTime'))
            if last_inventory_time and last_status_time:
                device.last_seen = max(last_inventory_time, last_status_time)
            else:
                device.last_seen = last_inventory_time or last_status_time

            if device_raw.get(EXTRA_INVENTORY) and isinstance(device_raw.get(EXTRA_INVENTORY), list):
                self._fill_dell_ome_device_inventory_fields(device_raw.get(EXTRA_INVENTORY), device)

            self._fill_dell_ome_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching DellOme Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.
        :param devices_raw_data: the raw data we get.
        :return:
        """
        for device_raw, device_inventory_raw in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching DellOme Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'async_chunks',
                    'type': 'integer',
                    'title': 'Async chunks in parallel'
                }
            ],
            'required': [
                'async_chunks'
            ],
            'pretty_name': 'Dell OpenManage Enterprise Configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls):
        return {
            'async_chunks': DEFAULT_ASYNC_CHUNKS_SIZE
        }

    def _on_config_update(self, config):
        self.__async_chunks = config.get('async_chunks') or DEFAULT_ASYNC_CHUNKS_SIZE
