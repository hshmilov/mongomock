import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.connection import RESTException
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import int_or_none, parse_bool_from_raw

from dns_made_easy_adapter.connection import DnsMadeEasyConnection
from dns_made_easy_adapter.client_id import get_client_id
from dns_made_easy_adapter.consts import SOURCE_TYPE_BY_ID, API_ENDPOINT_BASE
from dns_made_easy_adapter.structures import DnsMadeEasyDeviceInstance, \
    DnsMadeEasyNameServer, DnsMadeEasyDomain

logger = logging.getLogger(f'axonius.{__name__}')


class DnsMadeEasyAdapter(AdapterBase):
    class MyDeviceAdapter(DnsMadeEasyDeviceInstance):
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
        connection = DnsMadeEasyConnection(
            domain=client_config['domain'],
            apikey=client_config['api_key'],
            secret_key=client_config['secret_key'],
            verify_ssl=client_config['verify_ssl'],
            https_proxy=client_config.get('https_proxy'),
            proxy_username=client_config.get('proxy_username'),
            proxy_password=client_config.get('proxy_password')
        )
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as err:
            message = f'Error connecting to client with domain ' \
                      f'{client_config.get("domain")}, reason: {str(err)}'
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection

        :return: A json with all the attributes returned from the server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema DnsMadeEasyAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Host Name or IP Address',
                    'type': 'string',
                    'default': API_ENDPOINT_BASE
                },
                {
                    'name': 'api_key',
                    'title': 'API Key',
                    'type': 'string'
                },
                {
                    'name': 'secret_key',
                    'title': 'Secret Key',
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
                'api_key',
                'secret_key',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @staticmethod
    def _parse_nameservers(nameservers_raw: list) -> list:
        """
        This method will take a list of nameserver data and parse out
        the available fields for each nameserver. Some nameserver types
        have limited information, so all fields may not be populated. We
        then use this data to create a class instance of DnsMadeEasyNameServer,
        which is appended to a list and returned to the caller.

        :param nameservers_raw: A list of nameserver data as a dictionary
        :return nameservers: A list of DnsMadeEasyNameServer objects
        """
        nameservers = list()
        if not isinstance(nameservers_raw, list):
            raise ValueError(f'Malformed raw nameserver data. Expected a list, '
                             f'got {type(nameservers_raw)}: {str(nameservers_raw)}')

        for nameserver in nameservers_raw:
            if isinstance(nameserver, dict):
                ns = DnsMadeEasyNameServer(
                    ipv6=nameserver.get('ipv6'),
                    ipv4=nameserver.get('ipv4'),
                    fqdn=nameserver.get('fqdn'),
                    gtd_location_id=nameserver.get('gtdLocationId'),
                    group_id=nameserver.get('groupId'),
                    id=nameserver.get('id')
                )
            elif isinstance(nameserver, str):
                ns = DnsMadeEasyNameServer(
                    fqdn=nameserver
                )
            else:
                continue

            nameservers.append(ns)

        return nameservers

    # pylint: disable=invalid-triple-quote
    def _parse_enriched_domain_data(self,
                                    enriched_data: dict,
                                    domain_object: DnsMadeEasyDomain):
        """
        Take the passed enriched data and updates the attributes of the
        existing domain_object with this additional data.

        :param enriched_data: A dictionary containing information about
        the domain.
        :param domain_object: A DnsMadeEasyDomain object.
        """
        if not isinstance(enriched_data, dict):
            raise ValueError(f'Malformed enriched domain data. Expected a dict, '
                             f'got {type(enriched_data)}: {str(enriched_data)}')

        domain_object.vanity_id = int_or_none(enriched_data.get('vanityId'))
        domain_object.soa_id = int_or_none(enriched_data.get('soaID'))
        domain_object.template_id = int_or_none(enriched_data.get('templateId'))
        domain_object.transfer_acl_id = int_or_none(enriched_data.get('transferAclId'))
        domain_object.axfr_servers = enriched_data.get('axfrServer')

        # populate domain nameservers
        try:
            domain_ns = enriched_data.get('nameServers')
            if isinstance(domain_ns, list):
                domain_object.nameservers = self._parse_nameservers(nameservers_raw=domain_ns)
            else:
                logger.warning(f'Malformed domain nameservers. Expected '
                               f'a list, got {type(domain_ns)}:'
                               f'{str(domain_ns)}')
        except Exception:
            logger.exception(
                f'Unable to create nameservers for domain {domain_object.dnsme_id}: '
                f'{str(enriched_data.get("nameservers"))}')

        # populate delegate nameservers
        # this is different from nameservers and vanity nameservers b/c
        # it is a list of strings, not a list of dicts
        try:
            delegate_ns = enriched_data.get('delegateNameServers')
            if isinstance(delegate_ns, list):
                domain_object.delegate_nameservers = self._parse_nameservers(
                    nameservers_raw=delegate_ns)
            else:
                if delegate_ns is not None:
                    logger.warning(f'Malformed delegate nameservers. Expected '
                                   f'a list, got {type(delegate_ns)}: '
                                   f'{str(delegate_ns)}')
        except Exception:
            logger.exception(
                f'Unable to create delegated nameservers for {domain_object.dnsme_id}: '
                f'{str(enriched_data.get("delegate_nameservers"))}')

        # populate vanity nameservers
        try:
            vanity_ns = enriched_data.get('vanityNameServers')
            if isinstance(vanity_ns, list):
                domain_object.vanity_nameservers = self._parse_nameservers(
                    nameservers_raw=vanity_ns)
            else:
                if vanity_ns is not None:
                    logger.warning(
                        f'Malformed vanity nameservers. Expected '
                        f'a list, got {type(vanity_ns)}: '
                        f'{str(vanity_ns)}')
        except Exception:
            logger.exception(
                f'Unable to create vanity nameservers for {domain_object.dnsme_id}: '
                f'{str(enriched_data.get("vanity_nameservers"))}')

    @staticmethod
    def _parse_basic_domain_data(basic_data_raw: dict) -> DnsMadeEasyDomain:
        try:
            dnsme_domain = DnsMadeEasyDomain(
                dnsme_id=int_or_none(basic_data_raw.get('id')),
                dnsme_name=basic_data_raw.get('name'),
                created=parse_date(basic_data_raw.get('created')),
                folder_id=int_or_none(basic_data_raw.get('folderId')),
                gtd_enabled=parse_bool_from_raw(basic_data_raw.get('gtdEnabled')),
                updated=parse_date(basic_data_raw.get('updated')),
                process_multi=parse_bool_from_raw(basic_data_raw.get('processMulti')),
                active_third_parties=basic_data_raw.get('activeThirdParties'),
                pending_action_id=int_or_none(basic_data_raw.get('pendingActionId')),
            )
            return dnsme_domain

        except Exception as err:
            logger.exception(f'Problem parsing basic domain data: {str(err)}')

    # pylint: disable=too-many-statements, too-many-branches
    def _fill_dns_made_easy_device_fields(self, record: dict, device_raw: dict, device: MyDeviceAdapter):
        try:
            # process domain information
            basic_data = device_raw.get('basic_domain_data')
            if isinstance(basic_data, dict):
                domain_object = self._parse_basic_domain_data(basic_data_raw=basic_data)

                enriched_data = device_raw.get('enriched')
                if isinstance(enriched_data, dict):
                    self._parse_enriched_domain_data(
                        enriched_data=enriched_data,
                        domain_object=domain_object
                    )
                else:
                    logger.warning(
                        f'Malformed domain (enriched) data. Expected a '
                        f'dict, got {type(basic_data)}: {str(basic_data)}')

                if domain_object:
                    device.dnsme_domain = domain_object
            else:
                logger.warning(f'Malformed domain (basic) data. Expected a dict,'
                               f' got {type(basic_data)}: {str(basic_data)}')
        except Exception as err:
            logger.exception(f'Unable to parse domain information: {str(err)}')
            # fallthrough

        subdomain_source = record.get('source')
        if not isinstance(subdomain_source, int):
            logger.warning(f'Malformed subdomain source. Expected an int, got '
                           f'{type(subdomain_source)}: {str(subdomain_source)}')
            subdomain_source = -1  # resolves as 'Unknown'
        source: str = SOURCE_TYPE_BY_ID.get(subdomain_source)

        try:
            device.subdomain_name = record.get('name')
            device.ip_alias_or_server = record.get('value')
            device.record_type = record.get('type')
            device.record_id = record.get('id')
            device.source = source
            device.ttl = int_or_none(record.get('ttl'))
            device.gtd_location = record.get('gtdLocation')
            device.source_id = int_or_none(record.get('sourceId'))
            device.failover = parse_bool_from_raw(record.get('failover'))
            device.failed = parse_bool_from_raw(record.get('failed'))
            device.monitor = parse_bool_from_raw(record.get('monitor'))
            device.hard_link = parse_bool_from_raw(record.get('hardLink'))
            device.dynamic_dns = parse_bool_from_raw(record.get('dynamicDns'))
            device.keywords = record.get('keywords')
            device.title = record.get('title')
            device.redirect_type = record.get('redirectType')
            device.mx_level = int_or_none(record.get('mxLevel'))
            device.srv_weight = int_or_none(record.get('weight'))
            device.srv_priority = int_or_none(record.get('priority'))
            device.srv_port = int_or_none(record.get('port'))

        except Exception:
            logger.exception(
                f'Failed populating instance for device {device_raw}')
            raise

    def _create_device(self, record: dict, device_raw: dict, device: MyDeviceAdapter):
        """
        Parse the shared/common data and generic adapter fields.

        :param record: A dict representing a subdomain (domain record)
        :param device_raw: A dict representing the full domain data (subdomains/domains/etc)
        :param device: A MyDeviceAdapter object to populate.
        """
        try:
            device_id = int_or_none(record.get('id'))
            if device_id is None:
                logger.warning(f'Bad device with no ID {str(device_raw)}')
                return None

            device.id = f'{str(device_id)}_{record.get("name") or ""}'
            device.hostname = f'{str(record.get("name"))}.{device_raw.get("name")}'
            device.name = record.get('name')

            record_type = record.get('type')
            if isinstance(record_type, str):
                if record_type == 'A':
                    device.add_ips_and_macs(ips=record.get('value'))

            try:
                self._fill_dns_made_easy_device_fields(record, device_raw, device)
            except Exception as err:
                logger.exception(f'Failed to populate DNS Made Easy device: '
                                 f'{str(err)}')

            device.set_raw(record)

            return device
        except Exception as err:
            logger.exception(
                f'Problem with fetching DnsMadeEasy Device for {record}: '
                f'{str(err)}')

            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw_data in devices_raw_data:
            logger.debug(f'DNS device_raw_data: {str(device_raw_data)}')
            if not device_raw_data:
                continue

            records = device_raw_data.get('records')
            if not isinstance(records, list):
                raise ValueError(f'Malformed domain records. Expected a list, '
                                 f'got {type(records)}: {str(records)}')
            try:
                for record in records:
                    device = self._create_device(
                        record,
                        device_raw_data,
                        self._new_device_adapter())
                    if device:
                        yield device
            except Exception:
                logger.exception(f'Problem fetching DNSMadeEasy Device in '
                                 f'{device_raw_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
