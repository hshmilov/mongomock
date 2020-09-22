import datetime
import logging
from re import match

from typing import Optional, List

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.clients.illumio.connection import IllumioConnection
from axonius.clients.illumio.consts import DEFAULT_API_PORT, \
    SECONDS_IN_A_DAY, IPV4_REGEX
from axonius.devices.device_adapter import AGENT_NAMES
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_bool_from_raw, int_or_none
from illumio_adapter.client_id import get_client_id
from illumio_adapter.structures import IllumioDeviceInstance, \
    IllumioDeviceCondition, IllumioDeviceTag, IllumioDeviceLabel, \
    IllumioDeviceInterface, IllumioDeviceWorkload, IllumioLatestEvent, \
    IllumioRuleset, IllumioScope, IllumioRule, IllumioLabelResolver, \
    IllumioEndpoint, IllumioIpTablesRule, IllumioIpTablesStatement

logger = logging.getLogger(f'axonius.{__name__}')


class IllumioAdapter(AdapterBase):
    class MyDeviceAdapter(IllumioDeviceInstance):
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
        connection = IllumioConnection(domain=client_config.get('domain'),
                                       verify_ssl=client_config.get('verify_ssl'),
                                       https_proxy=client_config.get('https_proxy'),
                                       proxy_username=client_config.get('proxy_username'),
                                       proxy_password=client_config.get('proxy_password'),
                                       port=client_config.get('port'),
                                       org_id=client_config.get('org_id'),
                                       username=client_config.get('username'),
                                       password=client_config.get('password'))
        with connection:
            pass  # check that the connection credentials are valid
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

        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema IllumioAdapter expects from configs.

        NOTES:
            port:     The default port varies depending upon the setup
                        of the service and if it is on-prem or SaaS.
            username: This "username" is a quasi user name that is generated
                        by the service when an API key is created. It
                        takes the form of "api_#############"
            password: The password is the actual API key. Weird... I know.
            org_id:   This is a critical piece of information. There may be
                        several organizations in a single Illumio instance.
                        Each will require a separate connection to be configured.

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
                    'name': 'port',
                    'title': 'Port',
                    'type': 'integer',
                    'default': DEFAULT_API_PORT
                },
                {
                    'name': 'username',
                    'title': 'Authentication User Name',
                    'type': 'string'
                },
                {
                    'name': 'password',
                    'title': 'API Secret',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'org_id',
                    'title': 'Organization ID',
                    'type': 'string'
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
                'port',
                'username',
                'password',
                'org_id',
                'verify_ssl'
            ],
            'type': 'array'
        }

    # pylint: disable=too-many-branches, too-many-statements
    def _fill_illumio_device_fields(self,
                                    device_raw: dict,
                                    rulesets: list,
                                    device: MyDeviceAdapter):
        if not isinstance(device_raw, dict):
            message = f'Malformed device raw. Expected a dict, got ' \
                      f'{type(device_raw)}: {str(device_raw)}'
            logger.warning(message)
            raise ValueError(message)

        labels_raw = device_raw.get('labels')
        if isinstance(labels_raw, list):
            device.labels = self._parse_labels(labels_raw)
        else:
            if labels_raw is not None:
                logger.warning(f'Malformed device labels. Expected a list, got '
                               f'{type(labels_raw)}: {str(labels_raw)}')

        interfaces_raw = device_raw.get('interfaces')
        if isinstance(interfaces_raw, list):
            device.interfaces = self._parse_interfaces(interfaces_raw)
        else:
            if interfaces_raw is not None:
                logger.warning(f'Malformed device interfaces. Expected a list, '
                               f'got {type(interfaces_raw)}: '
                               f'{str(interfaces_raw)}')

        workloads_raw = device_raw.get('workloads')
        if isinstance(workloads_raw, list):
            device.workloads = self._parse_workloads(workloads_raw)
            workload_labels = self._parse_workload_labels(workloads_raw)
            if not isinstance(workload_labels, list):
                logger.warning(f'Malformed workload labels. Expected a list, '
                               f'got {type(workload_labels)}: '
                               f'{str(workload_labels)}')
                workload_labels = list()

            rulesets_raw = rulesets
            if isinstance(rulesets_raw, list) and workload_labels is not None:
                device.rulesets = self._parse_rulesets(rulesets_raw, workload_labels)
            else:
                if rulesets_raw is not None:
                    logger.warning(
                        f'Malformed rulesets. Expected a list, got '
                        f'{type(rulesets_raw)} and {str(rulesets_raw)}')
        else:
            if workloads_raw is not None:
                logger.warning(
                    f'Malformed device workloads. Expected a list, got '
                    f'{type(workloads_raw)}: {str(workloads_raw)}')

        container_cluster_raw = device_raw.get('container_cluster')
        if isinstance(container_cluster_raw, dict):
            device.container_cluster = self._parse_tag_data(raw_tag_data=container_cluster_raw)
        else:
            if container_cluster_raw is not None:
                logger.warning(
                    f'Malformed device container cluster. Expected a dict, got '
                    f'{type(container_cluster_raw)}: {str(container_cluster_raw)}')

        conditions_raw = device_raw.get('conditions')
        if isinstance(conditions_raw, list):
            device.conditions = self._parse_conditions(conditions_raw)
        else:
            if conditions_raw is not None:
                logger.warning(
                    f'Malformed device conditions. Expected a list, got '
                    f'{type(conditions_raw)}: {str(conditions_raw)}')

        matching_issuer_name = device_raw.get('secure_connect')
        if isinstance(matching_issuer_name, dict):
            secure_connect = matching_issuer_name.get('matching_issuer_name')
        else:
            logger.warning(f'Malformed secure connect. Expected a dict, '
                           f'got {type(matching_issuer_name)}: '
                           f'{str(matching_issuer_name)}')
            secure_connect = None

        created = device_raw.get('created_by')
        if isinstance(created, dict):
            created_by = created.get('href')
        else:
            logger.warning(f'Malformed created by data. Expected a dict, got '
                           f'{type(created)}: {str(created)}')
            created_by = None

        try:
            # ven schema
            device.href = device_raw.get('href')
            device.status = device_raw.get('status')
            device.activation_type = device_raw.get('activation_type')
            device.active_pce_fqdn = device_raw.get('active_pce_fqdn')
            device.target_pce_fqdn = device_raw.get('target_pce_fqdn')
            device.secure_connect = secure_connect
            device.last_goodbye_at = parse_date(device_raw.get('last_goodbye_at'))
            device.created_by = created_by
            device.updated_at = parse_date(device_raw.get('updated_at'))
            device.caps = device_raw.get('caps')
            # agent schema (leaving them here due to documentation issues)
            device.online = parse_bool_from_raw(device_raw.get('online'))
            device.mode = device_raw.get('mode')
            device.uptime_seconds = int_or_none(device_raw.get('uptime_seconds'))
            device.ip_tables_saved = parse_bool_from_raw(device_raw.get('ip_tables_saved'))
            device.log_traffic = parse_bool_from_raw(device_raw.get('log_traffic'))
        except Exception:
            logger.exception(f'Failed creating instance for device {device_raw}')

    @staticmethod
    def _parse_workload_labels(workloads_raw: list) -> Optional[List[str]]:
        """
        Pull the workload labels (HREFs) out of the raw data and return
        it as a list to the caller.

        :param workloads_raw: Full data defining a workload. We pull out
        only the labels from this data.
        :return workload_labels: A list of strings that point to the
        individual workloads.
        """
        if not isinstance(workloads_raw, list):
            logger.warning(f'Malformed raw workloads data. Expected a list, got '
                           f'{type(workloads_raw)}: {str(workloads_raw)}')
            return None

        workload_labels = list()

        for workload_raw in workloads_raw:
            if not isinstance(workload_raw, dict):
                message = f'Malformed workload raw data. Expected a dict, got ' \
                          f'{type(workload_raw)}: {str(workload_raw)}'
                logger.warning(message)
                continue

            labels = workload_raw.get('labels')
            if not isinstance(labels, list):
                message = f'Unable to process workload labels. Expected a ' \
                          f'list, got {type(labels)}: {str(labels)}'
                logger.warning(message)
                continue

            for label in labels:
                if not isinstance(label, dict):
                    message = f'Malformed workload label. Expected a dict, got ' \
                              f'{type(label)}: {str(label)}'
                    logger.warning(message)
                    continue

                workload_label = label.get('href')
                if not isinstance(workload_label, str):
                    logger.warning(f'Malformed workload label. Expected a '
                                   f'string, got {type(workload_label)}: '
                                   f'{str(workload_label)}')
                    continue

                workload_labels.append(workload_label)

        return workload_labels

    # pylint: disable=too-many-nested-blocks
    def _parse_rulesets(self, rulesets_raw: list, workload_labels: list) -> Optional[List[IllumioRuleset]]:
        """
        Work through the full ruleset data and, if there is a match to a
        workload label, create an IllumioRuleset object. A list of these
        objects is returned to the caller.

        :param rulesets_raw: Full ruleset data as a list of dicts.
        :param workload_labels: A list of HREF strings that point to
        workloads.
        :return rulesets: A list of IllumioRuleset objects
        """
        if not isinstance(rulesets_raw, list):
            logger.warning(f'Malformed raw rulesets data. Expected a list, got '
                           f'{type(rulesets_raw)}: {str(rulesets_raw)}')
            return None

        if not isinstance(workload_labels, list):
            logger.warning(f'Malformed workload labels data. Expected a list, '
                           f'got {type(workload_labels)}: {str(workload_labels)}')
            return None

        rulesets = list()

        try:
            for ruleset_raw in rulesets_raw:
                if not isinstance(ruleset_raw, dict):
                    logger.warning(f'Malformed ruleset raw data. Expected a '
                                   f'dict, got {type(ruleset_raw)}:'
                                   f'{str(ruleset_raw)}')
                    continue

                scopes = ruleset_raw.get('scopes')
                if not isinstance(scopes, list):
                    message = f'Malformed ruleset scopes. Expected a list, ' \
                              f'got {type(scopes)}: {str(scopes)}'
                    logger.warning(message)
                    raise ValueError(message)

                for scope in scopes:
                    if isinstance(scope, dict):
                        # this is the only value buried here
                        ruleset_label = scope.get('label')
                        if not isinstance(ruleset_label, dict):
                            logger.warning(f'Malformed ruleset label. Expected '
                                           f'a dict, got {type(ruleset_label)}: '
                                           f'{str(ruleset_label)}')
                            continue

                        ruleset_label_href = ruleset_label.get('href')
                        if not isinstance(ruleset_label_href, str):
                            logger.warning(
                                f'Malformed ruleset label HREF. Expected '
                                f'a string, got {type(ruleset_label)}: '
                                f'{str(ruleset_label)}')
                            continue

                        # if labels match populate workload with ruleset data
                        if ruleset_label in workload_labels:
                            ruleset_scopes = None
                            try:
                                ruleset_scopes = self._parse_ruleset_scopes(scopes)
                            except Exception as err:
                                logger.exception(f'Unable to parse ruleset '
                                                 f'scopes: {str(err)}')

                            ruleset_rules = None
                            try:
                                rules_raw = ruleset_raw.get('rules')
                                if isinstance(rules_raw, list):
                                    ruleset_rules = self._parse_ruleset_rules(rules_raw)
                                else:
                                    if rules_raw is not None:
                                        logger.warning(
                                            f'Malformed ruleset rules. Expected '
                                            f'a list, got {type(rules_raw)}: '
                                            f'{str(rules_raw)}')
                            except Exception as err:
                                logger.exception(f'Unable to parse ruleset '
                                                 f'rules: {str(err)}')

                            ip_tables_rules = None
                            try:
                                iptables_raw = ruleset_raw.get('ip_tables_rules')
                                if isinstance(iptables_raw, list):
                                    ip_tables_rules = self._parse_ip_tables_rules(iptables_raw)
                                else:
                                    logger.warning(
                                        f'Malformed ip tables raw data. Expected '
                                        f'a list, got {type(iptables_raw)}: '
                                        f'{str(iptables_raw)}')
                            except Exception as err:
                                logger.exception(f'Unable to parse iptables '
                                                 f'rules: {str(err)}')

                            workload_ruleset = IllumioRuleset(
                                href=ruleset_raw.get('href'),
                                created_at=parse_date(ruleset_raw.get('created_at')),
                                created_by=ruleset_raw.get('created_by'),
                                updated_at=parse_date(ruleset_raw.get('updated_at')),
                                updated_by=ruleset_raw.get('updated_by'),
                                deleted_at=parse_date(ruleset_raw.get('deleted_at')),
                                deleted_by=ruleset_raw.get('deleted_by'),
                                update_type=ruleset_raw.get('update_type'),
                                name=ruleset_raw.get('name'),
                                description=ruleset_raw.get('description'),
                                external_dataset=ruleset_raw.get('external_dataset'),
                                external_data_reference=ruleset_raw.get('external_data_reference'),
                                enabled=parse_bool_from_raw(ruleset_raw.get('enabled')),
                                scopes=ruleset_scopes,
                                rules=ruleset_rules,
                                ip_tables_rules=ip_tables_rules
                            )
                            rulesets.append(workload_ruleset)
        except Exception as err:
            logger.exception(f'Unable to parse rulesets: {str(err)}')

        return rulesets

    def _parse_ruleset_rules(self, rules_raw: list) -> Optional[List[IllumioRule]]:
        """
        This is a rather long function that takes the raw rules data
        and uses it to create a list of IllumioRule objects, which are
        returned to the caller.

        :param rules_raw: Full raw rules data as a list of dicts
        :return ruleset_rules: A list of IllumioRule objects
        """
        if not isinstance(rules_raw, list):
            logger.warning(f'Malformed raw ruleset rules data. Expected '
                           f'a list, got {type(rules_raw)}: {str(rules_raw)}')
            return None

        ruleset_rules = list()

        for rule_raw in rules_raw:
            if not isinstance(rule_raw, dict):
                logger.warning(f'Malformed ruleset rule. Expected a dict, got '
                               f'a {type(rule_raw)}: {str(rule_raw)}')
                return None

            data_type = 'ingress services'

            ingress_services = None
            ingress_services_raw = rule_raw.get('ingress_services')
            if isinstance(ingress_services_raw, list):
                ingress_services = self._parse_device_tag(
                    devices_data_raw=ingress_services_raw,
                    data_type=data_type
                )
            else:
                if ingress_services_raw is not None:
                    logger.warning(f'Malformed {data_type} data. Expected '
                                   f'a list, got {type(ingress_services_raw)}: '
                                   f'{str(ingress_services_raw)}')

            resolve_labels_as = None
            resolve_labels_raw = rule_raw.get('resolve_labels_as')
            if isinstance(resolve_labels_raw, dict):
                resolve_labels_as = self._parse_resolve_labels(resolve_labels_raw)
            else:
                if resolve_labels_raw is not None:
                    logger.warning(
                        f'Malformed ruleset resolve labels data. Expected '
                        f'a dict, got {type(resolve_labels_raw)}: '
                        f'{str(resolve_labels_raw)}')

            providers = None
            providers_raw = rule_raw.get('providers')
            if isinstance(providers_raw, list):
                providers = self._parse_providers(providers_raw)
            else:
                if providers_raw is not None:
                    logger.warning(
                        f'Malformed ruleset providers. Expected a list, '
                        f'got {type(providers_raw)}: {str(providers_raw)}')

            consumers = None
            consumers_raw = rule_raw.get('consumers')
            if isinstance(consumers_raw, list):
                consumers = self._parse_consumers(consumers_raw)
            else:
                if consumers_raw is not None:
                    logger.warning(
                        f'Malformed ruleset consumers. Expected a list, '
                        f'got {type(consumers_raw)}: {str(consumers_raw)}')

            data_type = 'consuming security principals'

            consuming_security_principals = None
            csps_raw = rule_raw.get('consuming_security_principals')
            if isinstance(csps_raw, list):
                consuming_security_principals = self._parse_device_tag(
                    devices_data_raw=csps_raw,
                    data_type=data_type
                )
            else:
                if csps_raw is not None:
                    logger.warning(
                        f'Malformed ruleset {data_type}.Expected a list, '
                        f'got {type(csps_raw)}: {str(csps_raw)}')

            ip_tables_rules = None
            iptables_rules_raw = rule_raw.get('ip_tables_rules')
            if isinstance(iptables_rules_raw, list):
                ip_tables_rules = self._parse_ip_tables_rules(iptables_rules_raw)
            else:
                if iptables_rules_raw is not None:
                    logger.warning(
                        f'Malformed ruleset iptables rules. Expected a '
                        f'list, got {type(iptables_rules_raw)}: '
                        f'{str(iptables_rules_raw)}')

            rule = IllumioRule(
                href=rule_raw.get('href'),
                enabled=parse_bool_from_raw(rule_raw.get('enabled')),
                description=rule_raw.get('description'),
                external_data_set=rule_raw.get('external_data_set'),
                external_data_reference=rule_raw.get('external_data_reference'),
                ingress_services=ingress_services,
                resolve_labels_as=resolve_labels_as,
                sec_connect=parse_bool_from_raw(rule_raw.get('sec_connect')),
                stateless=parse_bool_from_raw(rule_raw.get('stateless')),
                machine_auth=parse_bool_from_raw(rule_raw.get('machine_auth')),
                providers=providers,
                consumers=consumers,
                consuming_security_principals=consuming_security_principals,
                unscoped_consumers=parse_bool_from_raw(rule_raw.get('unscoped_consumers')),
                update_type=rule_raw.get('update_type'),
                ip_tables_rules=ip_tables_rules
            )
            ruleset_rules.append(rule)

        return ruleset_rules

    def _parse_ip_tables_rules(self, iptables_rules_raw: list) -> Optional[List[IllumioIpTablesRule]]:
        """
        Pull the iptables rules, if used, and create a list of
        IllumioIpTablesRule objects that are returned to the caller.

        :param iptables_rules_raw: Full raw iptables rule data as a list of dicts
        :return iptables_rules: A list of IllumioIpTablesRule objects
        """
        if not isinstance(iptables_rules_raw, list):
            logger.warning(f'Malformed raw iptables rules data. Expected '
                           f'a list, got {type(iptables_rules_raw)}: '
                           f'{str(iptables_rules_raw)}')
            return None

        iptables_rules = list()

        for iptables_rule_raw in iptables_rules_raw:
            if not isinstance(iptables_rule_raw, dict):
                logger.warning(f'Malformed raw iptables rule data. Expected a '
                               f'dict, got {type(iptables_rule_raw)}: '
                               f'{str(iptables_rule_raw)}')
                continue

            statements = None
            statements_raw = iptables_rule_raw.get('statements')
            if isinstance(statements_raw, list):
                statements = self._parse_iptables_statements(statements_raw)
            else:
                if statements_raw is not None:
                    logger.warning(
                        f'Malformed raw iptables statements. Expected a '
                        f'list, got {type(statements_raw)}: '
                        f'{str(statements_raw)}')

            actors = None
            actors_raw = iptables_rule_raw.get('actors')
            if isinstance(actors_raw, list):
                actors = self._parse_actors(actors_raw)
            else:
                if actors_raw is not None:
                    logger.warning(
                        f'Malformed raw iptables actors data. Expected a '
                        f'list, got {type(actors_raw)}: '
                        f'{str(actors_raw)}')

            rule = IllumioIpTablesRule(
                href=iptables_rule_raw.get('href'),
                enabled=parse_bool_from_raw(iptables_rule_raw.get('enabled')),
                description=iptables_rule_raw.get('description'),
                statements=statements,
                actors=actors,
                ip_version=iptables_rule_raw.get('ip_version')
            )
            iptables_rules.append(rule)

        return iptables_rules

    @staticmethod
    def _parse_actors(actors_raw: list) -> Optional[List[IllumioEndpoint]]:
        """
        Create a list of IllumioIpTablesActor objects from the passed
        raw actors data.

        :param actors_raw: Raw data describing iptables actors
        :return actors: A list of IllumioIpTablesActor objects
        """
        if not isinstance(actors_raw, list):
            logger.warning(f'Malformed raw iptables actors data. Expected '
                           f'a list, got {type(actors_raw)}: {str(actors_raw)}')
            return None

        actors = list()

        for actor_raw in actors_raw:
            if not isinstance(actor_raw, dict):
                logger.warning(f'Malformed iptables actors. Expected a dict, '
                               f'got {type(actor_raw)}: {str(actor_raw)}')
                continue

            actor = IllumioEndpoint(
                actors=actor_raw.get(actors),  # looks like a list, but the docs say str
                label=IllumioDeviceTag(href=actor_raw.get('label')),
                label_group=IllumioDeviceTag(href=actor_raw.get('label_group')),
                workload=IllumioDeviceTag(href=actor_raw.get('workload'))
            )
            actors.append(actor)

        return actors

    @staticmethod
    def _parse_iptables_statements(statements_raw: list) -> Optional[List[IllumioIpTablesStatement]]:
        """
        Take the passed raw iptables statement data and create a list of
        IllumioIpTablesStatement objects to return to the caller.

        :param statements_raw: Raw iptables statement data
        :return statements: A list of IllumioIpTablesStatement objects
        """
        if not isinstance(statements_raw, list):
            logger.warning(f'Malformed raw iptables statements data. Expected '
                           f'a list, got {type(statements_raw)}: '
                           f'{str(statements_raw)}')
            return None

        statements = list()

        for statement_raw in statements_raw:
            if not isinstance(statement_raw, dict):
                logger.warning(f'Malformed iptables statement. Expected a dict, '
                               f'got {type(statement_raw)}: {str(statement_raw)}')
                continue

            statement = IllumioIpTablesStatement(
                table_name=statement_raw.get('table_name'),
                chain_name=statement_raw.get('chain_name'),
                parameters=statement_raw.get('parameters')
            )
            statements.append(statement)

        return statements

    @staticmethod
    def _parse_device_tag(devices_data_raw: list, data_type: str) -> Optional[List[IllumioDeviceTag]]:
        """
        Take the passed raw device data and generate a list of
        IllumioDeviceTag objects. This function is generic and is used
        for the processing of multiple attributes.

        :param devices_data_raw: Raw device data as a list of dicts
        :param data_type: Primarily used for logging/exception purposes,
        but defines the type of attribute that this tag belongs to
        :return device_tags: A list of IllumioDeviceTag objects
        """
        if not isinstance(devices_data_raw, list):
            logger.warning(f'Malformed raw {data_type} tag data. Expected a '
                           f'list, got {type(devices_data_raw)}: '
                           f'{str(devices_data_raw)}')
            return None

        device_tags = list()

        for device_data_raw in devices_data_raw:
            if not isinstance(device_data_raw, dict):
                logger.warning(f'Malformed raw device data. Expected a dict, '
                               f'got {type(device_data_raw)}: '
                               f'{str(device_data_raw)}')
                continue

            device_tag = IllumioDeviceTag(
                href=device_data_raw.get('href'),
                name=device_data_raw.get('name')
            )
            device_tags.append(device_tag)

        return device_tags

    @staticmethod
    def _parse_consumers(consumers_raw: list) -> Optional[List[IllumioEndpoint]]:
        """
        Create a list of IllumioEndpoint objects that define consumers
        of a particular workload.

        :param consumers_raw: Raw data about a workload consumer
        :return consumers: A list of IllumioEndpoint objects.
        """
        if not isinstance(consumers_raw, list):
            logger.warning(f'Malformed raw consumers data. Expected a '
                           f'list, got {type(consumers_raw)}: '
                           f'{str(consumers_raw)}')
            return None

        consumers = list()

        for consumer_raw in consumers_raw:
            if isinstance(consumer_raw, dict):
                consumer = IllumioEndpoint(
                    actors=consumer_raw.get('actors'),
                    label=IllumioDeviceTag(href=consumer_raw.get('label')),
                    label_group=IllumioDeviceTag(href=consumer_raw.get('label_group')),
                    workload=IllumioDeviceTag(href=consumer_raw.get('workload')),
                    virtual_service=IllumioDeviceTag(href=consumer_raw.get('virtual_service')),
                    ip_list=IllumioDeviceTag(href=consumer_raw.get('ip_list'))
                )
                consumers.append(consumer)
            else:
                logger.warning(f'Unable to parse raw consumer. Expected a '
                               f'dict, got {type(consumers_raw)}: '
                               f'{str(consumers_raw)}')

        return consumers

    @staticmethod
    def _parse_providers(providers_raw: list) -> Optional[List[IllumioEndpoint]]:
        """
        Create a list of IllumioEndpoint objects that define providers
        of a particular workload.

        :param providers_raw: Raw data about a workload provider
        :return providers: A list of IllumioEndpoint objects.
        """
        if not isinstance(providers_raw, list):
            logger.warning(f'Malformed raw providers data. Expected a '
                           f'list, got {type(providers_raw)}: '
                           f'{str(providers_raw)}')
            return None

        providers = list()

        for provider_raw in providers_raw:
            if isinstance(provider_raw, dict):
                provider = IllumioEndpoint(
                    actors=provider_raw.get('actors'),
                    label=IllumioDeviceTag(href=provider_raw.get('label')),
                    label_group=IllumioDeviceTag(href=provider_raw.get('label_group')),
                    workload=IllumioDeviceTag(href=provider_raw.get('workload')),
                    virtual_service=IllumioDeviceTag(href=provider_raw.get('virtual_service')),
                    virtual_server=IllumioDeviceTag(href=provider_raw.get('virtual_server')),
                    ip_list=IllumioDeviceTag(href=provider_raw.get('ip_list'))
                )
                providers.append(provider)
            else:
                logger.warning(f'Unable to parse raw provider. Expected a '
                               f'dict, got {type(provider_raw)}: '
                               f'{str(provider_raw)}')

        return providers

    @staticmethod
    def _parse_resolve_labels(resolve_labels_raw: dict) -> Optional[IllumioLabelResolver]:
        if not isinstance(resolve_labels_raw, dict):
            logger.warning(f'Malformed raw label resolver data. Expected a '
                           f'dict, got {type(resolve_labels_raw)}: '
                           f'{str(resolve_labels_raw)}')
            return None

        resolve_labels = IllumioLabelResolver(
            providers=resolve_labels_raw.get('providers'),
            consumers=resolve_labels_raw.get('consumers')
        )

        return resolve_labels

    @staticmethod
    def _parse_ruleset_scopes(scopes_raw: list) -> Optional[List[IllumioScope]]:
        """
        Create a list of IllumioScope objects from the raw ruleset scope
        data.

        :param scopes_raw: The raw ruleset scope data
        :return ruleset_scopes: A list of IllumioScope objects
        """
        if not isinstance(scopes_raw, list):
            logger.warning(f'Malformed raw scopes data. Expected a list, got '
                           f'{type(scopes_raw)}: {str(scopes_raw)}')
            return None

        ruleset_scopes = list()

        for scope_raw in scopes_raw:
            if not isinstance(scope_raw, dict):
                logger.warning(f'Malformed ruleset scope. Expected a dict, '
                               f'got {type(scope_raw)}: {str(scope_raw)}')
                continue

            scope = IllumioScope(
                label=scope_raw.get('label'),
                label_group=scope_raw.get('label_group')
            )
            ruleset_scopes.append(scope)

        return ruleset_scopes

    @staticmethod
    def _parse_labels(labels_raw: list) -> Optional[List[IllumioDeviceLabel]]:
        """
        Create a list of IllumioDeviceLabel objects from the raw workload
        label data.

        :param labels_raw: The raw data defining a workload label
        :return labels: A list of IllumioDeviceLabel objects
        """
        if not isinstance(labels_raw, list):
            logger.warning(f'Malformed raw labels data. Expected a list, got '
                           f'{type(labels_raw)}: {str(labels_raw)}')
            return None

        labels = list()

        for label_raw in labels_raw:
            if isinstance(label_raw, dict):
                label = IllumioDeviceLabel(
                    href=label_raw.get('href'),
                    name=label_raw.get('name'),
                    key=label_raw.get('key'),
                    value=label_raw.get('value')
                )
                labels.append(label)
            else:
                logger.warning(f'Malformed raw label. Expected a dict, got '
                               f'{type(label_raw)}: {str(label_raw)}')
        return labels

    def _parse_interfaces(self, interfaces_raw: list) -> Optional[List[IllumioDeviceInterface]]:
        """
        Create a list of IllumioDeviceInterface objects that describe a
        VENs network interfaces.

        :param interfaces_raw: The raw data defining a network interface
        :return interfaces: A list of IllumioDeviceInterface objects
        """
        if not isinstance(interfaces_raw, list):
            logger.warning(
                f'Malformed raw interfaces data. Expected a list, got '
                f'{type(interfaces_raw)}: {str(interfaces_raw)}')

            return None

        interfaces = list()

        for interface_raw in interfaces_raw:
            if isinstance(interface_raw, dict):
                network_raw = interface_raw.get('network')
                if isinstance(network_raw, dict):
                    network = self._parse_tag_data(raw_tag_data=network_raw)
                else:
                    logger.warning(f'Malformed network data. Expected a dict, '
                                   f'got {type(network_raw)}: {str(network_raw)}')
                    network = None

                interface = IllumioDeviceInterface(
                    name=interface_raw.get('name'),
                    link_state=interface_raw.get('link_state'),
                    address=interface_raw.get('address'),
                    cidr_block=int_or_none(interface_raw.get('cidr_block')),
                    default_gateway_address=interface_raw.get('default_gateway_address'),
                    network=network,
                    network_detection_mode=interface_raw.get('network_detection_mode'),
                    friendly_name=interface_raw.get('friendly_name')
                )
                interfaces.append(interface)

        return interfaces

    @staticmethod
    def _parse_tag_data(raw_tag_data: dict) -> Optional[IllumioDeviceTag]:
        """
        Create an IllumioDeviceTag object from the HREF and name of an
        Illumio device (network, container, etc.) object.

        :param raw_tag_data: Raw data defining a VENs attributes
        :return: An IllumioDeviceTag object
        """
        if not isinstance(raw_tag_data, dict):
            logger.warning(f'Malformed raw tag data. Expected a dict, got '
                           f'{type(raw_tag_data)}: {str(raw_tag_data)}')
            return None

        return IllumioDeviceTag(
            href=raw_tag_data.get('href'),
            name=raw_tag_data.get('name')
        )

    def _parse_workloads(self, workloads_raw: list) -> Optional[List[IllumioDeviceWorkload]]:
        """
        Create a list of IllumioDeviceWorkload objects from the raw workload
        data.

        :param workloads_raw: A list of dicts defining discovered workloads
        :return workloads: A list of IllumioDeviceWorkload objects
        """
        if not isinstance(workloads_raw, list):
            logger.warning(f'Malformed raw workloads data. Expected a list, '
                           f'got {type(workloads_raw)}: {str(workloads_raw)}')
            return None

        workloads = list()

        for workload_raw in workloads_raw:
            if not isinstance(workload_raw, dict):
                logger.warning(f'Malformed raw workload data. Expected a dict, '
                               f'got {type(workload_raw)}: {str(workload_raw)}')
                return None

            workload_labels = workload_raw.get('labels')
            if isinstance(workload_labels, list):
                labels = self._parse_labels(workload_labels)
            else:
                logger.warning(
                    f'Malformed workload labels. Expected a list, got '
                    f'{type(workload_labels)}: {str(workload_labels)}')
                labels = None

            workload_interfaces = workload_raw.get('interfaces')
            if isinstance(workload_interfaces, list):
                interfaces = self._parse_interfaces(workload_interfaces)
            else:
                logger.warning(
                    f'Malformed device interfaces. Expected a list, got '
                    f'{type(workload_interfaces)}: {str(workload_interfaces)}')
                interfaces = None

            workload = IllumioDeviceWorkload(
                href=workload_raw.get('href'),
                name=workload_raw.get('name'),
                hostname=workload_raw.get('hostname'),
                os_id=workload_raw.get('os_id'),
                os_detail=workload_raw.get('os_detail'),
                labels=labels,
                # we extract the following in _create_device and add to ips
                public_ip=workload_raw.get('public_ip'),
                interfaces=interfaces,
                security_policy_applied_at=parse_date(workload_raw.get('security_policy_applied_at')),
                security_policy_received_at=parse_date(workload_raw.get('security_policy_received_at')),
                log_traffic=parse_bool_from_raw(workload_raw.get('log_traffic')),
                mode=workload_raw.get('mode'),
                visibility_level=workload_raw.get('visibility_level'),
                online=workload_raw.get('online')
            )
            workloads.append(workload)

        return workloads

    def _parse_conditions(self, conditions_raw: list) -> Optional[List[IllumioDeviceCondition]]:
        if not isinstance(conditions_raw, list):
            logger.warning(f'Malformed raw device conditions. Expected a list, '
                           f'got {type(conditions_raw)}: {str(conditions_raw)}')
            return None

        conditions = list()

        for condition_raw in conditions_raw:
            if isinstance(condition_raw, dict):
                latest_event_raw = condition_raw.get('latest_event')
                if isinstance(latest_event_raw, dict):
                    latest_event = self._parse_latest_event(latest_event_raw)
                else:
                    logger.warning(
                        f'Malformed latest event. Expected a dict, got '
                        f'{type(latest_event_raw)}: {str(latest_event_raw)}')
                    latest_event = None

                condition = IllumioDeviceCondition(
                    first_reported_timestamp=parse_date(condition_raw.get('first_reported_timestamp')),
                    latest_event=latest_event
                )
                conditions.append(condition)
            else:
                logger.warning(f'Malformed raw condition. Expected a dict, got '
                               f'{type(condition_raw)}: {str(condition_raw)}')

        return conditions

    @staticmethod
    def _parse_latest_event(latest_event_raw: dict) -> Optional[IllumioLatestEvent]:
        if not isinstance(latest_event_raw, dict):
            logger.warning(f'Malformed raw latest event. Expected a dict, got '
                           f'{type(latest_event_raw)}: {str(latest_event_raw)}')
            return None

        latest_event = IllumioLatestEvent(
            notification_type=latest_event_raw.get('notification_type'),
            severity=latest_event_raw.get('severity'),
            href=latest_event_raw.get('href'),
            # the docs don't describe how the following should look, but hint it is a dict
            info=latest_event_raw.get('info'),
            timestamp=parse_date(latest_event_raw.get('timestamp'))
        )

        return latest_event

    def _create_device(self, device_raw: dict, rulesets: list, device: MyDeviceAdapter):
        """
        In this function and _fill_illumio_device_fields, I am attempting to
        minimize the likelihood of issues by covering the attributes for the
        VEN-style API and the agent-style API. The documentation is not
        currently in a stable (up to date) state.

        :param device_raw: A dict containing the raw device information
        :param rulesets: A list containing the raw ruleset data
        :param device: A MyDeviceAdapter class instance that will be
        populated with the device_raw data
        :return device: A MyDeviceAdapter class instance
        """
        try:
            device_id = device_raw.get('id') or device_raw.get('uid')
            if device_id is None:
                logger.warning(f'Bad device with no ID {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('name') or '')

            device.name = device_raw.get('name')
            device.description = device_raw.get('description')
            device.hostname = device_raw.get('hostname')

            # pull workloads to extract public IPs
            workloads = device_raw.get('workloads')
            if isinstance(workloads, list):
                ips = list()
                for workload in workloads:
                    if not isinstance(workload, dict):
                        logger.warning(f'Malformed workload data. Expected a '
                                       f'dict, got {type(workload)}: '
                                       f'{str(workload)}')
                        continue

                    public_ip = workload.get('public_ip')
                    if isinstance(public_ip, str) and match(IPV4_REGEX, public_ip):
                        ips.append(public_ip)

                device.add_ips_and_macs(ips=ips)

            # the docs don't mention how either of these are formatted, so this is just a guess
            os_info = f'{device_raw.get("os_id") or ""} {device_raw.get("os_detail") or ""}'.strip()
            if os_info:
                device.figure_os(os_string=os_info)

            # both version attributes are documented, so attempting to capture both.
            # ven_version is more recent and agent_version is likely deprecated
            agent_version = device_raw.get('agent_version')
            ven_version = device_raw.get('version')
            if agent_version:
                device.add_agent_version(version=agent_version, agent=AGENT_NAMES.illumio)
            if ven_version:
                device.add_agent_version(version=ven_version, agent=AGENT_NAMES.illumio)

            uptime_in_seconds = int_or_none(device_raw.get('uptime_seconds'))
            if uptime_in_seconds:
                uptime_in_days = uptime_in_seconds / SECONDS_IN_A_DAY
                device.uptime = int_or_none(uptime_in_days)

            # these are not well defined in docs, so try to find the most recent
            last_heartbeat = parse_date(device_raw.get('last_heartbeat_at'))
            last_goodbye = parse_date(device_raw.get('last_goodbye_at'))

            if isinstance(last_goodbye, datetime.datetime) and \
                    isinstance(last_heartbeat, datetime.datetime):
                latest_date = max(last_goodbye, last_heartbeat)
            else:
                latest_date = last_heartbeat or last_goodbye

            device.last_seen = latest_date
            device.first_seen = parse_date(device_raw.get('created_at'))

            self._fill_illumio_device_fields(device_raw, rulesets, device)

            device.set_raw(device_raw)
            return device
        except Exception:
            logger.exception(f'Problem fetching Illumio Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        """
        Gets raw data and yields Device objects.

        :param devices_raw_data: the raw data we get as a dict with 2
        fields; vens and rulesets
        """
        for device_raw, rulesets in devices_raw_data:
            if not device_raw:
                continue
            try:
                # noinspection PyTypeChecker
                device = self._create_device(device_raw, rulesets, self._new_device_adapter())
                if device:
                    yield device
            except Exception:
                logger.exception(f'Problem with fetching Illumio Device for {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
