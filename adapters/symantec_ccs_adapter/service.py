import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.fields import Field
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import is_domain_valid, parse_bool_from_raw, float_or_none, int_or_none
from axonius.clients.rest.connection import RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from symantec_ccs_adapter.connection import SymantecCcsConnection
from symantec_ccs_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-statements, too-many-branches
class SymantecCcsAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        device_type = Field(str, 'Device Type')
        device_path = Field(str, 'Device Path')
        evaluated_compliance_scores = Field(float, 'Evaluated Compliance Scores')
        evaluated_risk_scores = Field(float, 'Evaluated Risk Scores')
        max_risk_scores = Field(float, 'Max Risk Scores')
        asset_site = Field(str, 'Site')
        asset_location = Field(str, 'Location')
        asset_sourceid = Field(str, 'Source ID')
        asset_source = Field(str, 'Source')
        asset_department = Field(str, 'Department')
        asset_custodian = Field(str, 'Custodian')
        asset_integrity = Field(int, 'Integrity')
        asset_confidentiality = Field(int, 'Confidentiality')
        asset_availability = Field(int, 'Availability')
        asset_docker_version = Field(str, 'Docker Version')
        asset_is_tomcat_running = Field(bool, 'Is Tomcat Running (unix)')
        asset_is_was_installed = Field(bool, 'Is WAS Installed')
        asset_ssh_version = Field(str, 'SSH Version')
        asset_ssh_port_no = Field(int, 'SSH Port Number')
        asset_is_apache_installed = Field(bool, 'Is Apache Installed (unix)')
        asset_is_win_machine_server = Field(bool, 'Is Windows Machine Server')
        asset_is_win_machine_bdc = Field(bool, 'Is Windows Machine BDC')
        asset_is_win_machine_pdc = Field(bool, 'Is Windows Machine PDC')
        asset_sharepoint_version = Field(str, 'Sharepoint Version')
        asset_iis_version = Field(str, 'IIS Version')
        asset_vmware_vcenter_server = Field(str, 'VMWare vCenter Server')
        asset_apache_tomcat_server = Field(str, 'Apache Tomcat Server')

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
        connection = SymantecCcsConnection(domain=client_config['domain'],
                                           verify_ssl=client_config['verify_ssl'],
                                           https_proxy=client_config.get('https_proxy'),
                                           username=client_config['username'],
                                           password=client_config['password'])
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
        The schema SymantecCcsAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Symantec CCS Domain',
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
    def _create_device(device_raw, device: MyDeviceAdapter):
        try:
            device_id = device_raw.get('ID')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('DisplayName') or '')
            attributes = device_raw.get('Attributes')
            if not isinstance(attributes, list):
                attributes = []

            raw_fields = dict()
            for attribute_raw in attributes:
                attribute_name = attribute_raw.get('Name')
                attribute_value_single = attribute_raw.get('Value')
                attribute_values_multi = attribute_raw.get('Values')

                if attribute_raw.get('IsMultiValued'):
                    raw_fields[attribute_name] = attribute_values_multi
                else:
                    raw_fields[attribute_name] = attribute_value_single

            # attributes dictionary

            # Generic
            device.first_seen = parse_date(raw_fields.get('whenCreated'))
            device.last_seen = parse_date(raw_fields.get('whenChanged'))

            # windows / linux
            if is_domain_valid(raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-DomainWorkgroupName')):
                device.domain = raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-DomainWorkgroupName')

            device.hostname = raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-HostName') or \
                raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-HostMachine')

            try:
                os_raw = (raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-OSVersionType') or '') + ' ' + \
                         (raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-OSSystem') or '') + ' ' + \
                         (raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-OSDistributionField') or '') + ' ' + \
                         (raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-OSVersionString') or '')

                device.figure_os(os_raw)
                device.os.kernel_version = raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-KERNELVERSION')

                win_major = raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-OSMajorVersionNumber')
                win_minor = raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-OSMinorVersionNumber')

                if win_major is not None:
                    device.os.major = win_major

                if win_minor is not None:
                    device.os.minor = win_minor
            except Exception:
                logger.exception(f'Problem parsing OS')

            try:
                ip_addresses = raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-IPAddresses') or \
                    raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-TCPIPAddresses')

                if not isinstance(ip_addresses, list):
                    ip_addresses = ip_addresses.split(',')

                ip_addresses = [ip.strip() for ip in ip_addresses]
                ip_addresses = [ip[:-3].strip() if '%' in ip else ip for ip in ip_addresses]

                device.add_nic(ips=ip_addresses)
            except Exception:
                logger.exception(f'Problem parsing IP addresses')

            device.asset_is_apache_installed = parse_bool_from_raw(
                raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-IsApacheInstalled')
            )

            device.asset_is_was_installed = parse_bool_from_raw(
                raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-IsWASInstalled')
            )

            device.asset_is_tomcat_running = parse_bool_from_raw(
                raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-IsTomcatRunning')
            )

            device.asset_ssh_port_no = int_or_none(raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-SSHPortNo'))
            device.asset_ssh_version = raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-SSHVersion')
            if raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-DockerVersion') != 'Not Installed':
                device.asset_docker_version = raw_fields.get('symc-csm-AssetSystem-Asset-Unix-Machine-DockerVersion')

            device.asset_is_win_machine_server = parse_bool_from_raw(
                raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-Server')
            )

            device.asset_is_win_machine_bdc = parse_bool_from_raw(
                raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-BDC')
            )
            device.asset_is_win_machine_pdc = parse_bool_from_raw(
                raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-PDC')
            )

            device.asset_sharepoint_version = raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-SHAREPOINTVERSION')
            device.asset_iis_version = raw_fields.get('symc-csm-AssetSystem-Asset-Wnt-Machine-IISVERSION')
            device.asset_vmware_vcenter_server = raw_fields.get(
                'symc-csm-AssetSystem-Asset-Wnt-Machine-VMWAREVCENTERSERVER')
            device.asset_apache_tomcat_server = raw_fields.get(
                'symc-csm-AssetSystem-Asset-Wnt-Machine-APACHETOMCATSEREVR')

            # AssetBase

            device.asset_confidentiality = int_or_none(
                raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Confidentiality')
            )

            device.asset_integrity = int_or_none(
                raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Integrity')
            )

            device.asset_availability = int_or_none(
                raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Availability')
            )

            device.asset_custodian = raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Custodian')
            device.asset_department = raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Department')
            device.asset_location = raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Location')
            device.owner = raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Owner')
            device.asset_site = raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Site')
            device.asset_sourceid = raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-SourceID')
            device.asset_source = raw_fields.get('symc-csm-AssetSystem-Asset-AssetBase-Source')

            # device_raw attrs
            device.device_type = (device_raw.get('Type') or {}).get('DisplayName')
            device.device_path = device_raw.get('Path')

            device.evaluated_compliance_scores = float_or_none(
                device_raw.get('symc-csm-AssetSystem-Asset-AssetBase-EvaluatedComplianceScores')
            )

            device.evaluated_risk_scores = float_or_none(
                device_raw.get('symc-csm-AssetSystem-Asset-AssetBase-EvaluatedRiskScores')
            )

            device.max_risk_scores = float_or_none(
                device_raw.get('symc-csm-AssetSystem-Asset-AssetBase-MaxRiskScores')
            )

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem with fetching SymantecCcs Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw, self._new_device_adapter())
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Agent]
