import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from digital_shadows_adapter.connection import DigitalShadowsConnection
from digital_shadows_adapter.client_id import get_client_id
from digital_shadows_adapter.structures import DigitalShadowsDeviceInstance, PortInfo, \
    IncidentData, VulnInfo, SocketInfo
from digital_shadows_adapter.consts import IP_PORT, VULNS, SOCKET

logger = logging.getLogger(f'axonius.{__name__}')


class DigitalShadowsAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DigitalShadowsDeviceInstance):
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
        connection = DigitalShadowsConnection(domain=client_config['domain'],
                                              verify_ssl=client_config['verify_ssl'],
                                              https_proxy=client_config.get('https_proxy'),
                                              username=client_config['api_key'],
                                              password=client_config['api_secret'])
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
        The schema DigitalShadowsAdapter expects from configs

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
                    'name': 'api_key',
                    'title': 'API Key',
                    'type': 'string'
                },
                {
                    'name': 'api_secret',
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
                'api_key',
                'api_secret',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _fill_digital_shadows_device_fields(device_raw: dict, device: MyDeviceAdapter):
        try:
            for obj_name, obj_data in device_raw:
                try:
                    incident_raw = obj_data.get('incident')
                    if not isinstance(incident_raw, dict):
                        incident_raw = {}
                    closed_source = incident_raw.get('closedSource')
                    if not isinstance(closed_source, bool):
                        closed_source = None
                    incident_obj = IncidentData(scope=incident_raw.get('scope'),
                                                type=incident_raw.get('type'),
                                                sub_type=incident_raw.get('subType'),
                                                severity=incident_raw.get('severity'),
                                                title=incident_raw.get('title'),
                                                published=parse_date(incident_raw.get('published')),
                                                closed_source=closed_source
                                                )
                    if obj_name == IP_PORT:
                        port_number = obj_data.get('portNumber')
                        if not isinstance(port_number, int):
                            continue
                        device.add_open_port(port_id=port_number)
                        port_obj = PortInfo(reverse_domain_name=obj_data.get('reverseDomainName'),
                                            port_number=port_number,
                                            transport=obj_data.get('transport'),
                                            discovered_open=parse_date(obj_data.get('discoveredOpen')),
                                            detected_closed=parse_date(obj_data.get('detectedClosed')),
                                            incident=incident_obj
                                            )
                        device.digital_shadows_ports_info.append(port_obj)
                    elif obj_name == VULNS:
                        device.add_vulnerable_software(cve_id=obj_data.get('cveId'))
                        vuln_obj = VulnInfo(discovered=parse_date(obj_data.get('discovered')),
                                            cve_id=obj_data.get('cveId'),
                                            determined_resolved=parse_date(obj_data.get('determinedResolved')),
                                            incident=incident_obj,
                                            reverse_domain_name=obj_data.get('reverseDomainName'))
                        device.digital_shadows_vulns_info.append(vuln_obj)
                    elif obj_name == SOCKET:
                        revoked = obj_data.get('revoked')
                        if not isinstance(revoked, bool):
                            revoked = None
                        issues = obj_data.get('issues')
                        if not isinstance(issues, list):
                            issues = None
                        socket_obj = SocketInfo(domain_name=obj_data.get('domainName'),
                                                incident=incident_obj,
                                                reverse_domain_name=obj_data.get('reverseDomainName'),
                                                discovered=parse_date(obj_data.get('discovered')),
                                                transport=obj_data.get('transport'),
                                                grade=obj_data.get('grade'),
                                                revoked=revoked,
                                                expires=parse_date(obj_data.get('expires')),
                                                issues=issues,
                                                certificate_common_name=obj_data.get('certificateCommonName'))
                        device.digital_shadows_socket_info.append(socket_obj)
                except Exception:
                    logger.exception(f'Problem with obj name and data {obj_name} ; {obj_data}')
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    def _create_device(self, device_raw: dict, device: MyDeviceAdapter):
        try:
            ip, ips_data = device_raw
            device_id = ip
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id
            device.add_nic(ips=[ip])
            device.add_public_ip(ip=ip)
            self._fill_digital_shadows_device_fields(ips_data, device)

            device.set_raw({'data': ips_data})

            return device
        except Exception:
            logger.exception(f'Problem with fetching DigitalShadows Device for {device_raw}')
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
                logger.exception(f'Problem with fetching DigitalShadows Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
