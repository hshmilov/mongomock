import datetime
import ipaddress
import logging

from axonius.utils.datetime import parse_date

from axonius.utils.json import to_json, from_json

from axonius.fields import Field, ListField

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.files import get_local_config_file
from openvas_adapter import consts
from openvas_adapter.connection import OpenvasConnection
from openvas_adapter.client_id import get_client_id
from openvas_adapter.fields import HostAssetIdentifier, OpenvasScanResult, OpenvasHostDetails, parse_owner

logger = logging.getLogger(f'axonius.{__name__}')


class OpenvasAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        comment = Field(str, 'Comment')
        severity = Field(int, 'Overall Severity')
        creation_time = Field(datetime.datetime, 'Creation Time')
        mod_time = Field(datetime.datetime, 'Modification Time')
        owner = Field(str, 'Owner')
        identifiers = ListField(HostAssetIdentifier, 'Host Asset Identifiers')
        host_details = ListField(OpenvasHostDetails, 'Host Details')
        asset_type = Field(str, 'Asset Type')
        writable = Field(bool, 'Writable')
        scan_results = ListField(OpenvasScanResult, 'Scan Results')
        in_use = Field(bool, 'In Use')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @classmethod
    def _test_reachability(cls, client_config):
        host = client_config.get('domain')
        port = cls._get_port(client_config)
        return OpenvasConnection.test_reachability(host, port=port)

    @classmethod
    def _get_port(cls, client_config):
        proto = cls._get_protocol(client_config)
        return client_config.get('port', proto.value)

    @staticmethod
    def _get_protocol(client_config):
        try:
            proto_name = client_config.get('gvm_protocol')
            return consts.GvmProtocols[proto_name]
        except KeyError:
            message = f'Invalid protocol: {proto_name}.'
            raise ClientConnectionException(message)

    @classmethod
    def get_connection(cls, client_config):
        proto = cls._get_protocol(client_config)
        port = cls._get_port(client_config)
        return OpenvasConnection(
            client_config['domain'],
            client_config['username'],
            client_config['password'],
            protocol=proto,
            port=port,
            ssh_username=client_config.get('ssh_username'),
            ssh_password=client_config.get('ssh_password'),
            # _debug_file_assets=client_config.get('_debug_file_assets'),
            # _debug_file_scans=client_config.get('_debug_file_scans')
        )

    def _connect_client(self, client_config):
        try:
            conn = self.get_connection(client_config)
            with conn:
                # test connection and auth
                pass
            return conn
        except Exception as e:
            message = 'Error connecting to server {0}, reason: {1}'.format(
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
        yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema OpenvasAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'OpenVAS host',
                    'type': 'string'
                },
                {
                    'name': 'username',
                    'title': 'OpenVAS user name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'OpenVAS password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'ssh_username',
                    'title': 'SSH user name',
                    'type': 'string'
                },
                {
                    'name': 'ssh_password',
                    'title': 'SSH password',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'gvm_protocol',
                    'title': 'OpenVAS connection protocol',
                    'type': 'string',
                    'enum': list(x.name for x in consts.GvmProtocols),
                    'default': consts.GvmProtocols.TLS.name,
                },
                {
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'description': 'Port (Default: 22 for SSH, 9390 for TLS)'
                },
                # {
                #     'name': '_debug_file_assets',
                #     'title': 'DEBUG asset file',
                #     'type': 'file',
                # },
                # {
                #     'name': '_debug_file_scans',
                #     'title': 'DEBUG scans file',
                #     'type': 'file',
                # },
            ],
            'required': [
                'domain',
                'username',
                'password',
                'gvm_protocol',
            ],
            'type': 'array'
        }

    @classmethod
    def _parse_ident(cls, device, ident):
        if not ident or not isinstance(ident, dict):
            return
        name = ident.get('name')
        value = ident.get('value')
        if name and isinstance(name, str):
            if name == 'hostname':
                device.hostname = value
            elif name == 'ip':
                cls._try_add_ip(device, value)
        try:
            device.identifiers.append(
                HostAssetIdentifier.from_dict(ident))
        except Exception as e:
            message = f'Failed to add identifier data {ident} for {device.id}: {str(e)}'
            logger.warning(message, exc_info=True)

    @staticmethod
    def _try_add_ip(device, ip_addr):
        def _find_ip(ip_address, nic_info):
            return ip_address in nic_info.ips
        try:
            ip_addr = int(ip_addr)
        except ValueError:
            ip_addr = str(ip_addr)
        try:
            ip = ipaddress.ip_address(ip_addr)
            is_known = any(_find_ip(str(ip), nic) for nic in device.network_interfaces)
            if str(ip) in device.public_ips or is_known:
                logger.debug(f'Device {device.id}: Got duplicate ip {ip_addr}, skipping.')
                return
            logger.debug(f'Adding IP to device {device.id}: {str(ip)}')
            try:
                device.add_public_ip(str(ip))
            except Exception:
                message = f'Failed to add public ip {str(ip)} for {device.id}'
                logger.warning(message)
            device.add_ips_and_macs(ips=[str(ip)])
        except Exception:
            message = f'Failed to add IP to device {device.id}: ip {ip_addr} is invalid.'
            logger.exception(message)

    @staticmethod
    def _parse_host(device, host):
        if not host or not isinstance(host, dict):
            return
        try:
            severity = host['severity']['value']
            device.severity = float(severity)
        except (ValueError, KeyError):
            logger.warning(f'Failed to parse severity from {host} for {device.id}')
        host_details = host.get('detail', [])
        if not host_details:
            return
        if isinstance(host_details, dict):
            host_details = [host_details]
        for host_detail in host_details:
            if not host_detail:
                continue
            if '_os_' in host_detail.get('name'):
                value = host_detail.get('value')
                try:
                    device.figure_os(host_detail['value'])
                except Exception as e:
                    logger.warning(f'Failed to figure os from {value} for {device.id}: {str(e)}')
            try:
                device.host_details.append(OpenvasHostDetails.from_dict(host_detail))
            except Exception as e:
                message = f'Failed to add details {host_detail}: {str(e)}'
                logger.warning(message)
                continue

    # pylint: disable=too-many-branches,too-many-statements
    def _create_device(self, device_raw):
        try:
            device = self._new_device_adapter()

            device_id = device_raw.get('@id')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name'))
            # Axonius generic stuff
            name = device_raw.get('name')
            device.name = name
            self._try_add_ip(device, name)
            # first_seen (creation date)
            try:
                device.first_seen = parse_date(device_raw.get('creation_time'))
            except Exception as e:
                message = f'Failed to parse first_seen (creation time) for {device.id}: {str(e)}'
                logger.warning(message)

            # Identifiers (IPs and hostname)
            ident_dict = device_raw.get('identifiers', {})
            idents = ident_dict.get('identifier')
            if not isinstance(idents, list):
                idents = [idents]
            for ident in idents:
                try:
                    self._parse_ident(device, ident)
                except Exception as e:
                    message = f'Error parsing identifier {to_json(ident)} for {device.id}: ' \
                              f'{str(e)}'
                    logger.warning(message, exc_info=True)

            # now try host information and os
            try:
                self._parse_host(device, device_raw.get('host'))
            except Exception as e:
                message = f'Failed to parse host information from {device_raw.get("host")}: ' \
                          f'{str(e)}'
                logger.warning(message, exc_info=True)

            # Try to identify user
            try:
                owner = parse_owner(device_raw.get('owner'))
                device.add_users(username=owner)
            except Exception as e:
                message = f'Failed to add related user to {device.id}: {str(e)}'
                logger.warning(message, exc_info=True)

            # And now for the simple stuff
            device.comment = device_raw.get('comment')
            device.owner = parse_owner(device_raw.get('owner'))
            device.asset_type = device_raw.get('type')
            device.writable = device_raw.get('writable', '0') == '1'
            device.in_use = device_raw.get('in_use', '0') == '1'

            # Finally, scan details!!!
            scan_details = device_raw.pop('x_scan_results', [])
            for scan in scan_details:
                try:
                    device.scan_results.append(
                        OpenvasScanResult.from_dict(scan)
                    )
                except Exception as e:
                    message = f'Failed to parse scan details for {device.id}: Scan {to_json(scan)}'
                    logger.warning(message, exc_info=True)

            # Aaaaand now finally the raw thingamajig
            device.set_raw(from_json(to_json(device_raw)))
            return device
        except Exception:
            logger.exception(f'Problem with fetching Openvas Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Network, AdapterProperty.Vulnerability_Assessment]
