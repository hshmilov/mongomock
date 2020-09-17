import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.itop.connection import ItopConnection
from axonius.devices.device_adapter import DeviceAdapterVlan
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from itop_adapter.client_id import get_client_id
from itop_adapter.structures import ItopDeviceInstance, ItopUserInstance, Ticket, NetworkDevice

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=logging-format-interpolation


class ItopAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(ItopDeviceInstance):
        pass

    class MyUserAdapter(ItopUserInstance):
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
        connection = ItopConnection(domain=client_config.get('domain'),
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
    # pylint: disable=arguments-differ
    def _query_users_by_client(client_name, client_data):
        """
        Get all users from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_user_list()

    @staticmethod
    def _clients_schema():
        """
        The schema ItopAdapter expects from configs

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
    # pylint: disable=too-many-statements
    def _fill_itop_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            device.org_id = int_or_none(device_raw.get('org_id'))
            device.business_criticity = device_raw.get('business_criticity')
            device.move_to_production = parse_bool_from_raw(device_raw.get('move2production'))
            device.location_id = int_or_none(device_raw.get('location_id'))
            device.status = device_raw.get('status')
            device.brand_id = device_raw.get('brand_id')
            device.brand_name = device_raw.get('brand_name')
            device.model_id = device_raw.get('model_id')
            device.asset_number = device_raw.get('asset_number')
            device.purchase_date = parse_date(device_raw.get('purchase_date'))
            device.end_of_warranty = parse_date(device_raw.get('end_of_warranty'))
            device.rack_id = device_raw.get('rack_id')
            device.rack_name = device_raw.get('rack_name')
            device.source = device_raw.get('source')
            device.region = device_raw.get('region_friendlyname')
            device.zone = device_raw.get('zone_friendlyname')
            device.country = device_raw.get('country_friendlyname')
            device.obsolescence_date = parse_date(device_raw.get('obsolescence'))
            device.itop_type = device_raw.get('networkdevicetype_id_friendlyname')

            tickets = []
            if isinstance(device_raw.get('tickets_list'), list):
                for ticket_raw in device_raw.get('tickets_list'):
                    if isinstance(ticket_raw, dict):
                        ticket = Ticket()
                        ticket.ticket_id = ticket_raw.get('ticket_id')
                        ticket.ticket_ref = ticket_raw.get('ticket_ref')
                        ticket.ticket_title = ticket_raw.get('ticket_title')
                        ticket.impact = ticket_raw.get('impact')
                        ticket.impact_code = ticket_raw.get('impact_code')
                        ticket.friendlyname = ticket_raw.get('friendlyname')
                        ticket.ticket_id_friendlyname = ticket_raw.get('ticket_id_friendlyname')
                        ticket.ticket_id_finalclass_recall = ticket_raw.get('ticket_id_finalclass_recall')
                        tickets.append(ticket)
            device.tickets = tickets

            network_devices = []
            if isinstance(device_raw.get('tickets_list'), list):
                for network_device_raw in device_raw.get('tickets_list'):
                    if isinstance(network_device_raw, dict):
                        network_device = NetworkDevice()
                        network_device.networkdevice_id = network_device_raw.get('networkdevice_id')
                        network_device.networkdevice_name = network_device_raw.get('networkdevice_name')
                        network_device.network_port = network_device_raw.get('network_port')
                        network_device.device_port = network_device_raw.get('device_port')
                        network_device.connection_type = network_device_raw.get('connection_type')
                        network_device.friendlyname = network_device_raw.get('friendlyname')
                        network_device.networkdevice_id_friendlyname = network_device_raw.get(
                            'networkdevice_id_friendlyname')
                        network_device.obsolescence_flag = network_device_raw.get(
                            'networkdevice_id_obsolescence_flag')
                        network_devices.append(network_device)
            device.network_devices = network_devices

        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    # pylint: disable=too-many-branches, too-many-nested-blocks
    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('key')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.description = device_raw.get('description')
            device.hostname = device_raw.get('sys_hostname')
            device.device_serial = device_raw.get('serialnumber')
            device.device_model = device_raw.get('model_name')
            device.physical_location = device_raw.get('location_name')

            services = device_raw.get('services_list')
            if isinstance(services, str):
                services = [services]
            for service in services:
                if isinstance(service, str):
                    device.add_service(name=service)

            softwares = device_raw.get('softwares_list')
            if isinstance(softwares, str):
                softwares = [softwares]
            for software in softwares:
                if isinstance(software, str):
                    device.add_installed_software(name=software)

            organization_unit = device_raw.get('organization_name')
            if isinstance(organization_unit, str):
                organization_unit = [organization_unit]
            device.organizational_unit = organization_unit

            if isinstance(device_raw.get('physicalinterface_list'), list):
                for physical_interface_raw in device_raw.get('physicalinterface_list'):
                    if not isinstance(physical_interface_raw, dict):
                        logger.warning(f'Couldnt fill interface information, received {physical_interface_raw}')
                        continue

                    ips = physical_interface_raw.get('ipaddress')
                    if isinstance(ips, str):
                        ips = [ips]

                    vlans = []
                    if isinstance(physical_interface_raw.get('vlans_list'), list):
                        for vlan_raw in physical_interface_raw.get('vlans_list'):
                            if not isinstance(vlan_raw, dict):
                                logger.warning(f'Could not fill vlan information, received {vlan_raw}')
                                continue

                            vlan = DeviceAdapterVlan()
                            vlan.name = vlan_raw.get('friendlyname')
                            vlan.tagid = vlan_raw.get('vlan_tag')
                            vlans.append(vlan)

                    device.add_nic(mac=physical_interface_raw.get('macaddress'),
                                   ips=ips,
                                   name=physical_interface_raw.get('name'),
                                   vlans=vlans,
                                   gateway=physical_interface_raw.get('ipgateway'),
                                   port=physical_interface_raw.get('interfaceport'))

            os_string = device_raw.get('iosversion_id_friendlyname')
            device.figure_os(os_string=os_string)

            self._fill_itop_device_fields(device_raw, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching Itop Device for {device_raw}')
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
                logger.exception(f'Problem with fetching Itop Device for {device_raw}')

    @staticmethod
    def _fill_itop_user_fields(user_raw: dict, user: MyUserAdapter):
        try:
            user.org_id = user_raw.get('org_id')
            user.notify = user_raw.get('notify')
            user.function = user_raw.get('function')
            user.user_class = user_raw.get('finalclass')
            user.obsolescence_date = parse_date(user_raw.get('obsolescence_date'))

        except Exception:
            logger.exception(f'Failed creating instance for user {user_raw}')

    def _create_user(self, user_raw: dict, user: MyUserAdapter):
        try:
            user_id = user_raw.get('key')
            if user_id is None:
                logger.warning(f'Bad user with no ID {user_raw}')
                return None
            user.id = str(user_id) + '_' + (user_raw.get('name') or '')

            user.display_name = user_raw.get('name')
            user.first_name = user_raw.get('first_name')
            user.user_status = user_raw.get('status')
            user.employee_number = user_raw.get('employee_number')
            user.mail = user_raw.get('email')
            user.user_telephone_number = user_raw.get('phone')
            user.user_manager = user_raw.get('manager_name')

            organization_unit = user_raw.get('org_name')
            if isinstance(organization_unit, str):
                organization_unit = [organization_unit]
            user.organizational_unit = organization_unit

            self._fill_itop_user_fields(user_raw, user)

            user.set_raw(user_raw)
            return user
        except Exception:
            logger.exception(f'Problem with fetching Itop User for {user_raw}')
            return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_raw_data):
        """
        Gets raw data and yields User objects.
        :param users_raw_data: the raw data we get.
        :return:
        """
        for user_raw in users_raw_data:
            if not user_raw:
                continue
            try:
                # noinspection PyTypeChecker
                user = self._create_user(user_raw, self._new_user_adapter())
                if user:
                    yield user
            except Exception:
                logger.exception(f'Problem with fetching Itop User for {user_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.UserManagement]
