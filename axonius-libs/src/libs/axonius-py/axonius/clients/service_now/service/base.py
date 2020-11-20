import logging
import re
from abc import abstractmethod
from datetime import timedelta
from typing import Optional, List, Callable

import chardet

from axonius.adapter_base import AdapterProperty, AdapterBase
from axonius.clients.service_now import consts
from axonius.clients.service_now.consts import InjectedRawFields
from axonius.clients.service_now.external import generic_service_now_query_devices_by_client, \
    generic_service_now_query_users_by_client
from axonius.clients.service_now.parse import get_reference_display_value
from axonius.clients.service_now.service.structures import RelativeInformationNode1, RelativeInformationLeaf, \
    MaintenanceSchedule, CiIpData, SnowComplianceException, SnowDeviceContract
from axonius.multiprocess.multiprocess import concurrent_multiprocess_yield
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import make_dict_from_csv, float_or_none, parse_bool_from_raw, int_or_none, is_valid_ip

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=invalid-name,too-many-nested-blocks,too-many-arguments,too-many-instance-attributes
# pylint: disable=too-many-return-statements, too-many-lines


class ServiceNowAdapterBase(AdapterBase):
    """
    Most of the ServiceNow Parsing logic occurs here
    Note: This also requires subclassing Configurable and implementing:
     * AdapterBase._clients_schema using SERVICE_NOW_CLIENTS_SCHEMA_ITEMS and SERVICE_NOW_CLIENTS_SCHEMA_REQUIRED
            class methods.
     *  Configurable._on_config_update by extending the existing implementation using super.
     *  Configurable._db_config_schema using SERVICE_NOW_DB_CONFIG_SCHEMA_ITEMS and
            SERVICE_NOW_DB_CONFIG_SCHEMA_REQUIRED class methods
     * Configurable._db_config_default using SERVICE_NOW_DB_CONFIG_DEFAULT class method
    """

    SERVICE_NOW_CLIENTS_SCHEMA_ITEMS = [
        {
            'name': 'install_status_file',
            'title': 'Install Status ENUM CSV File',
            'type': 'file'
        },
        {
            'name': 'operational_status_file',
            'title': 'Operational Status ENUM CSV File',
            'type': 'file'
        },
        {
            'name': 'verification_install_status_file',
            'title': 'Verification table install status ENUM CSV file',
            'type': 'file'
        },
        {
            'name': 'verification_operational_status_file',
            'title': 'Verification table operational status ENUM CSV file',
            'type': 'file'
        },
    ]
    SERVICE_NOW_CLIENTS_SCHEMA_REQUIRED = []
    SERVICE_NOW_DB_CONFIG_SCHEMA_ITEMS = [
        {
            'name': 'fetch_users_info_for_devices',
            'type': 'bool',
            'title': 'Fetch users data'
        },
        {
            'name': 'fetch_users',
            'type': 'bool',
            'title': 'Create users'
        },
        {
            'name': 'use_cached_users',
            'type': 'bool',
            'title': 'Use existing user data during device fetching'
        },
        {
            'name': 'fetch_ips',
            'type': 'bool',
            'title': 'Fetch IP addresses'
        },
        {
            'name': 'exclude_disposed_devices',
            'title': 'Exclude disposed and decommissioned devices',
            'type': 'bool'
        },
        {
            'name': 'exclude_no_strong_identifier',
            'title': 'Do not fetch devices without IP address, MAC address and serial number',
            'type': 'bool'
        },
        {
            'name': 'use_ci_table_for_install_status',
            'title': 'Use \'cmdb_ci\' table instead of \'alm_asset\' table for install status',
            'type': 'bool'
        },
        {
            'name': 'exclude_vm_tables',
            'type': 'bool',
            'title': 'Exclude VMs tables'
        },
        {
            'name': 'email_whitelist',
            'title': 'Users Email whitelist',
            'type': 'string'
        },
        {
            'name': 'fetch_only_active_users',
            'type': 'bool',
            'title': 'Fetch only active users'
        },
        {
            'name': 'install_status_exclude_list',
            'title': 'Install status number exclude list',
            'type': 'string'
        },
        {
            'name': 'fetch_only_virtual_devices',
            'title': 'Fetch only virtual devices',
            'type': 'bool'
        },
        {
            'name': 'fetch_operational_status',
            'type': 'bool',
            'title': 'Fetch operational status'
        },
        {
            'name': 'fetch_ci_relations',
            'type': 'bool',
            'title': 'Fetch device relations'
        },
        {
            'name': 'when_no_hostname_fallback_to_name',
            'type': 'bool',
            'title': 'When hostname does not exit, use asset name as hostname'
        },
        {
            'name': 'fetch_compliance_exceptions',
            'type': 'bool',
            'title': 'Fetch active compliance policy exceptions'
        },
        {
            'name': 'use_exclusion_field',
            'type': 'bool',
            'title': 'Do not fetch devices or users marked as excluded'
        },
        {
            'name': 'is_ram_in_gb',
            'type': 'bool',
            'title': 'RAM from source in GB'
        },
        {
            'name': 'fetch_software_product_model',
            'type': 'bool',
            'title': 'Fetch OS information from "cmdb_software_product_model"'
        },
        {
            'name': 'fetch_cmdb_model',
            'type': 'bool',
            'title': 'Fetch model information from "cmdb_model"'
        },
        {
            'name': 'fetch_business_unit_table',
            'type': 'bool',
            'title': 'Fetch business unit from \'business_unit\' table'
        },
        {
            'name': 'fetch_nics_table',
            'type': 'bool',
            'title': 'Fetch NIC information from \'cmdb_ci_network_adapter\' table'
        },
        {
            'name': 'fetch_installed_software',
            'type': 'bool',
            'title': 'Fetch Software package information from \'cmdb_sam_sw_install\' table'
        },
        {
            'name': 'contract_parent_numbers',
            'type': 'string',
            'title': 'Fetch Device contract information from \'ast_contract\''
                     ' for the following parent contract numbers',
        },
        {
            'name': 'diversiture_contract_parent_numbers',
            'type': 'string',
            'title': 'Fetch Device diversiture contract information from \'ast_contract\''
                     ' for the following parent contract numbers',
        },
        {
            'name': 'snow_last_updated',
            'title': 'Fetch devices updated in ServiceNow in the last X hours (0: All)',
            'type': 'number',
            'min': 0,
        },
        {
            'name': 'snow_user_last_created',
            'title': 'Fetch users created in ServiceNow in the last X hours (0: All)',
            'type': 'number',
            'min': 0,
        },
        {
            'name': 'use_dotwalking',
            'title': 'Use dotwalking queries',
            'type': 'bool',
        },
        {
            'name': 'dotwalking_per_request_limit',
            'title': 'Max dotwalking fields per request',
            'type': 'number',
            'min': 1,
            'max': consts.MAX_DOTWALKING_PER_REQUEST,
        },
    ]
    SERVICE_NOW_DB_CONFIG_SCHEMA_REQUIRED = [
        'fetch_users',
        'fetch_ips',
        'use_ci_table_for_install_status',
        'exclude_disposed_devices',
        'fetch_users_info_for_devices',
        'use_cached_users',
        'exclude_no_strong_identifier',
        'exclude_vm_tables',
        'fetch_only_active_users',
        'fetch_only_virtual_devices',
        'fetch_operational_status',
        'fetch_ci_relations',
        'when_no_hostname_fallback_to_name',
        'fetch_compliance_exceptions',
        'use_exclusion_field',
        'is_ram_in_gb',
        'fetch_software_product_model',
        'fetch_cmdb_model',
        'fetch_business_unit_table',
        'fetch_nics_table',
        'fetch_installed_software',
        'use_dotwalking',
    ]
    SERVICE_NOW_DB_CONFIG_DEFAULT = {
        'fetch_users': True,
        'fetch_ips': True,
        'fetch_users_info_for_devices': True,
        'use_cached_users': False,
        'exclude_disposed_devices': False,
        'exclude_no_strong_identifier': False,
        'use_ci_table_for_install_status': False,
        'exclude_vm_tables': False,
        'email_whitelist': None,
        'fetch_only_active_users': False,
        'install_status_exclude_list': None,
        'fetch_only_virtual_devices': False,
        'fetch_operational_status': True,
        'fetch_ci_relations': False,
        'when_no_hostname_fallback_to_name': False,
        'fetch_compliance_exceptions': False,
        'use_exclusion_field': False,
        'is_ram_in_gb': False,
        'fetch_software_product_model': True,
        'fetch_cmdb_model': True,
        'fetch_business_unit_table': False,
        'fetch_nics_table': True,
        'fetch_installed_software': False,
        'contract_parent_numbers': None,
        'diversiture_contract_parent_numbers': None,
        'snow_last_updated': 0,
        'snow_user_last_created': 0,
        'use_dotwalking': False,
        'dotwalking_per_request_limit': consts.DEFAULT_DOTWALKING_PER_REQUEST,
    }

    @abstractmethod
    def get_connection(self, client_config):
        pass

    @abstractmethod
    def get_connection_external(self) -> Callable:
        pass

    def _prepare_contract_parent_numbers(self):
        contract_parent_numbers = ''
        if self._contract_parent_numbers:
            contract_parent_numbers += self._contract_parent_numbers
        if self._diversiture_contract_parent_numbers:
            if contract_parent_numbers:
                contract_parent_numbers += ','
            contract_parent_numbers += self._diversiture_contract_parent_numbers
        return contract_parent_numbers

    def _connect_client(self, client_config):
        # get_connection will throw in case of any error in the connection
        self.get_connection(client_config)
        return (client_config,
                self.get_connection_external(),
                {
                    'fetch_users_info_for_devices': self.__fetch_users_info_for_devices,
                    'fetch_ci_relations': self.__fetch_ci_relations,
                    'fetch_compliance_exceptions': self._fetch_compliance_exceptions,
                    'fetch_software_product_model': self._fetch_software_product_model,
                    'fetch_cmdb_model': self._fetch_cmdb_model,
                    'fetch_installed_software': self._fetch_installed_software,
                    'fetch_business_unit_dict': self._fetch_business_unit_dict,
                    'fetch_nics_table': self._fetch_nics_table,
                    'last_seen_timedelta': self._snow_last_updated_threashold,
                    'user_last_created_timedelta': self._snow_user_last_created_threashold,
                    'contract_parent_numbers': self._prepare_contract_parent_numbers(),
                    'parallel_requests': self.__parallel_requests,
                    'use_dotwalking': self._use_dotwalking,
                    'dotwalking_per_request_limit': self._dotwalking_per_request_limit,
                    'use_cached_users': self._use_cached_users,
                    'plugin_name': self.plugin_name,
                })

    # pylint: disable=too-many-branches
    @staticmethod
    def _parse_raw_snow_ip(ip_address_raw):
        ip_addresses = None

        if isinstance(ip_address_raw, str):
            if '/' in ip_address_raw:
                ip_addresses = ip_address_raw.split('/')
            elif ',' in ip_address_raw:
                ip_addresses = ip_address_raw.split(',')
            elif ';' in ip_address_raw:
                ip_addresses = ip_address_raw.split(';')
            elif '&' in ip_address_raw:
                ip_addresses = ip_address_raw.split('&')
            elif 'and' in ip_address_raw:
                ip_addresses = ip_address_raw.split('and')
            elif r'\\\\' in ip_address_raw:
                # Example: 1.1.1.1\\\\1.1.1.1
                ip_addresses = ip_address_raw.split(r'\\\\')
            elif re.search(consts.RE_SQUARED_BRACKET_WRAPPED, ip_address_raw):
                # Example: [1.1.1.1] or [1.1.1.1][255.255.255.192]
                # Note: all of the use cases ive seen had only one ip (and at most an additional subnet),
                #       This implementation considers both as IPs in case this will actually be the case,
                #       at most the subnet will be ignored as invalid ip
                ip_addresses = re.findall(consts.RE_SQUARED_BRACKET_WRAPPED, ip_address_raw)
            elif ':' in ip_address_raw:
                # Example: 1.1.1.1:8000
                ip_addresses = [ip_address_raw.split(':')[0]]
            elif '(ilo' in ip_address_raw.lower():
                # Example: 1.1.1.1 (iLo 1.1.1.1) or 1.1.1.1 (iLo)
                ip_addresses = [ip_address_raw.split('(i', 1)[0]]
            elif '-' in ip_address_raw:
                # Example: 1.1.1.1 - VLAN2
                ip_addresses = [ip_address_raw.split('-')[0]]
            else:
                ip_addresses = [ip_address_raw]

        if isinstance(ip_addresses, list):
            ip_addresses = [ip.strip() for ip in ip_addresses
                            if isinstance(ip, str) and is_valid_ip(ip.strip())]

        return ip_addresses

    # pylint: disable=R0912,R0915,R0914
    def create_snow_device(self,
                           device_raw,
                           fetch_ips=True,
                           install_status_dict=None,
                           operational_status_dict=None,
                           verification_install_status_dict=None,
                           verification_operational_status_dict=None):
        got_nic = False
        got_serial = False
        if not install_status_dict:
            install_status_dict = consts.INSTALL_STATUS_DICT
        if not operational_status_dict:
            operational_status_dict = consts.INSTALL_STATUS_DICT
        try:
            if self._use_exclusion_field and parse_bool_from_raw(device_raw.get('u_exclude_from_discovery')):
                logger.debug(f'ignoring excluded device {device_raw.get("sys_id")}')
                return None
        except Exception:
            logger.warning(f'Failed handling exclusion of device')
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('sys_id')
            if not device_id:
                logger.warning(f'Problem getting id at {device_raw}')
                return None
            device.id = str(device_id) + '_' + (device_raw.get('name') or '')
            device.sys_id = str(device_id)
            device.table_type = device_raw.pop(InjectedRawFields.ax_device_type.value, None)
            device.category = device_raw.get('u_category') or device_raw.get('category')
            device.u_subcategory = device_raw.get('u_subcategory')
            device.asset_tag = device_raw.get('asset_tag')
            name = device_raw.get('name')
            device.name = name
            class_name = device_raw.get('sys_class_name')
            device.u_cloud_premises = device_raw.get('u_cloud_premises')
            device.u_bia_availability = device_raw.get('u_bia_availability')
            device.u_bia_confidentiality = device_raw.get('u_bia_confidentiality')
            device.u_bia_id = device_raw.get('u_bia_id')
            device.u_bia_integrity = device_raw.get('u_bia_integrity')
            device.u_bia_overall = device_raw.get('u_bia_overall')
            device.u_cloud_deployment_model = device_raw.get('u_cloud_deployment_model')
            device.u_cloud_hosted = device_raw.get('u_cloud_hosted')
            device.u_cloud_service_type = device_raw.get('u_cloud_service_type')
            device.u_crosssite_condition = device_raw.get('u_crosssite_condition')
            device.u_virtual_system_type = device_raw.get('u_virtual_system_type')
            device.u_heritage = (consts.U_HERITAGE_DICT.get(str(device_raw.get('u_heritage'))) or
                                 device_raw.get('u_heritage'))
            virtual = device_raw.get('virtual') or device_raw.get('u_is_virtual')
            if isinstance(virtual, str):
                device.is_virtual = virtual.lower() == 'true'
                if virtual.lower() != 'true' and self.__fetch_only_virtual_devices:
                    return None
            if self.__exclude_vm_tables is True and class_name and 'cmdb_ci_vm' in class_name:
                return None
            device.class_name = class_name

            subnets = []
            connected_subnet = device_raw.pop(InjectedRawFields.connected_subnet.value, None)
            if isinstance(connected_subnet, str) and '/' in connected_subnet:
                subnets.append(connected_subnet)

            try:
                ip_addresses = None
                ip_address = device_raw.get('ip_address')
                if fetch_ips and ip_address and not any(elem in ip_address for elem in ['DHCP',
                                                                                        '*',
                                                                                        'Stack',
                                                                                        'x',
                                                                                        'X']):
                    ip_addresses = self._parse_raw_snow_ip(ip_address)
                mac_address = device_raw.get('mac_address')
                if mac_address or ip_addresses:
                    got_nic = True
                    device.add_nic(mac_address, ip_addresses, subnets=subnets)
            except Exception:
                logger.warning(f'Problem getting NIC at {device_raw}', exc_info=True)
            try:
                support_group = device_raw.pop(InjectedRawFields.support_group.value, None)
                if isinstance(support_group, dict):
                    support_group = support_group.get('display_value')
                device.support_group = support_group
                u_director = device_raw.pop(InjectedRawFields.u_director.value, None)
                if isinstance(u_director, dict):
                    u_director = u_director.get('display_value')
                device.u_director = u_director
                u_manager = device_raw.pop(InjectedRawFields.u_manager.value, None)
                if isinstance(u_manager, dict):
                    u_manager = u_manager.get('display_value')
                device.u_manager = u_manager
                device.support_group_manager_company = device_raw.pop(InjectedRawFields.u_manager_company.value, None)
                device.support_group_manager_business_segment = \
                    device_raw.pop(InjectedRawFields.u_manager_business_segment.value, None)
            except Exception:
                logger.warning(f'Problem adding support group to {device_raw}', exc_info=True)

            try:
                mac_u = device_raw.get('u_mac_address')
                if mac_u:
                    device.add_nic(mac=mac_u)
            except Exception:
                logger.exception(f'Problem getting mac 2 for {device_raw}')

            os_title = device_raw.get('os') or device_raw.pop(InjectedRawFields.os_title.value, None)
            os_major_version = device_raw.pop(InjectedRawFields.major_version.value, None)
            os_minor_version = device_raw.pop(InjectedRawFields.minor_version.value, None)
            os_build_version = device_raw.pop(InjectedRawFields.build_version.value, None)
            u_operating_system = ''
            if os_major_version or os_minor_version or os_build_version:
                # Take new fields and add them
                u_operating_system = (f'{os_major_version or ""}'
                                      f'.{os_minor_version or ""}'
                                      f' {os_build_version or ""}')
            device.figure_os(' '.join([os_title or '',
                                       (device_raw.get('os_address_width') or ''),
                                       (u_operating_system or ''),
                                       (device_raw.get('os_domain') or ''),
                                       (device_raw.get('os_service_pack') or ''),
                                       (device_raw.get('os_version') or '')]))
            device.os.install_date = parse_date(device_raw.get('install_date'))
            model_u_classification = device_raw.pop(InjectedRawFields.model_u_classification.value, None)
            try:
                if isinstance(model_u_classification, str):
                    try:
                        # see if its an integer string, e.g. '6'
                        model_u_classification = int(model_u_classification)
                        # Fallthrough to int handling
                    except Exception:
                        # nope its an actual string
                        pass
                if isinstance(model_u_classification, int):
                    # Note: Translate classification into the correct string, default to the classification number
                    model_u_classification = (consts.MODEL_U_CLASSIFICATION_DICT.get(model_u_classification)
                                              or model_u_classification)
                device.model_u_classification = model_u_classification
            except Exception:
                logger.warning(f'Problem getting model classification at {model_u_classification}', exc_info=True)
            try:
                use_count = device_raw.get('use_count')
                if isinstance(use_count, int):
                    device.use_count = use_count
                use_units = device_raw.get('use_units')
                if isinstance(use_units, str):
                    device.use_units = use_units
                bandwidth = device_raw.get('bandwidth')
                if isinstance(bandwidth, int):
                    device.bandwidth = bandwidth
                snmp_sys_location = device_raw.get('snmp_sys_location')
                if isinstance(snmp_sys_location, str):
                    device.snmp_sys_location = snmp_sys_location
                u_audit_tools_checked = device_raw.get('u_audit_tools_checked')
                if isinstance(u_audit_tools_checked, str):
                    device.u_audit_tools_checked = u_audit_tools_checked
                u_audit_tools_pass = device_raw.get('u_audit_tools_pass')
                if isinstance(u_audit_tools_pass, str):
                    device.u_audit_tools_pass = u_audit_tools_pass
                u_backbone = device_raw.get('u_backbone')
                if isinstance(u_backbone, str):
                    device.u_backbone = u_backbone
                u_bill_ref_id = device_raw.get('u_bill_ref_id')
                if isinstance(u_bill_ref_id, str):
                    device.u_bill_ref_id = u_bill_ref_id
                u_circuit_id = device_raw.get('u_circuit_id')
                if isinstance(u_circuit_id, str):
                    device.u_circuit_id = u_circuit_id
                u_config_item_id = device_raw.get('u_config_item_id')
                if isinstance(u_config_item_id, str):
                    device.u_config_item_id = u_config_item_id
                u_ownership_ack = device_raw.get('u_ownership_ack')
                if isinstance(u_ownership_ack, str):
                    device.u_ownership_ack = u_ownership_ack
                u_port_speed = device_raw.get('u_port_speed')
                if isinstance(u_port_speed, str):
                    device.u_port_speed = u_port_speed
                u_previous_assigned_to = device_raw.get('u_previous_assigned_to')
                if isinstance(u_previous_assigned_to, str):
                    device.u_previous_assigned_to = u_previous_assigned_to
                u_previous_owned_by = device_raw.get('u_previous_owned_by')
                if isinstance(u_previous_owned_by, str):
                    device.u_previous_owned_by = u_previous_owned_by
                u_process_origin = device_raw.get('u_process_origin')
                if isinstance(u_process_origin, str):
                    device.u_process_origin = u_process_origin
                u_system_origin = device_raw.get('u_system_origin')
                if isinstance(u_system_origin, str):
                    device.u_system_origin = u_system_origin
                device.u_uninstall_date = parse_date(device_raw.get('u_uninstall_date'))
            except Exception:
                logger.warning(f'Failed parsing SNOW JSON fields', exc_info=True)
            device_model = device_raw.pop(InjectedRawFields.device_model.value, None)
            device.device_model = device_model
            device_serial = device_raw.get('serial_number') or ''
            try:
                if (device_serial or '').startswith('VMware'):
                    device_serial += (device_model or '')
                if not any(bad_serial in device_serial for bad_serial in
                           ['Pending Discovery',
                            'Virtual Machine',
                            'VMware Virtual Platform',
                            'AT&T', 'unknown',
                            'Instance']):
                    if device_serial:
                        got_serial = True
                    device.device_serial = device_serial
            except Exception:
                logger.warning(f'Problem getting serial at {device_raw}', exc_info=True)
            # pylint: disable=R1714
            try:
                ram_raw = float_or_none(device_raw.get('ram'))
                if ram_raw and ram_raw != -1:
                    device.total_physical_memory = ram_raw if self._is_ram_in_gb else ram_raw / 1024.0
            except Exception:
                logger.warning(f'Problem getting ram at {device_raw}', exc_info=True)
            try:
                alias = device_raw.get('u_alias')
                device.u_alias = alias
                host_name = device_raw.get('host_name') or device_raw.get('fqdn') or device_raw.get('u_fqdn')
                if host_name and name and name.lower() in host_name.lower():
                    device.hostname = host_name.split('.')[0].strip()
                else:
                    if self.__when_no_hostname_fallback_to_name and not host_name and name:
                        device.hostname = name.split('.')[0].strip()
                    elif alias and ',' in alias and '|' in name:
                        alias_list = alias.split(',')
                        for alias_raw in alias_list:
                            alias_raw = alias_raw.strip().lower()
                            if alias_raw and alias_raw != 'undefined':
                                device.hostname = alias_raw
            except Exception:
                logger.warning(f'Problem getting hostname in {device_raw}', exc_info=True)
            try:
                fqdn = device_raw.get('fqdn') or device_raw.get('u_fqdn')
                if isinstance(fqdn, str):
                    device.fqdn = fqdn
            except Exception:
                logger.warning(f'Problem getting FQDN in {device_raw}', exc_info=True)
            device.description = device_raw.get('short_description')
            device.snow_department = device_raw.pop(InjectedRawFields.snow_department.value, None)
            device.physical_location = device_raw.pop(InjectedRawFields.physical_location.value, None)

            install_status = device_raw.pop(InjectedRawFields.asset_install_status.value, None)
            try:
                try:
                    if install_status and not isinstance(install_status, str):
                        install_status = install_status_dict.get(install_status)
                except Exception:
                    logger.warning(f'Problem getting install status for {install_status}', exc_info=True)
                device.u_loaner = device_raw.pop(InjectedRawFields.asset_u_loaner.value, None)
                device.u_shared = device_raw.pop(InjectedRawFields.asset_u_shared.value, None)
                try:
                    device.first_deployed = parse_date(device_raw.pop(InjectedRawFields.asset_first_deployed.value,
                                                                      None))
                except Exception:
                    logger.warning(f'Problem getting first deployed at {device_raw}', exc_info=True)
                device.u_altiris_status = device_raw.pop(InjectedRawFields.asset_altiris_status.value, None)
                device.u_casper_status = device_raw.pop(InjectedRawFields.asset_casper_status.value, None)
                try:
                    device.substatus = device_raw.pop(InjectedRawFields.asset_substatus.value, None)
                except Exception:
                    logger.warning(f'Problem adding hardware status to {device_raw}', exc_info=True)
                try:
                    device.purchase_date = parse_date(device_raw.pop(InjectedRawFields.asset_purchase_date.value, None))
                except Exception:
                    logger.warning(f'Problem adding purchase date to {device_raw}', exc_info=True)
                device.u_last_inventory = parse_date(device_raw.pop(InjectedRawFields.asset_last_inventory.value, None))
                try:
                    snow_location = device_raw.pop(InjectedRawFields.snow_location.value, None)
                    if isinstance(snow_location, dict):
                        snow_location = snow_location.get('display_value')
                    device.snow_location = snow_location
                except Exception:
                    logger.warning(f'Problem adding assigned_to to {device_raw}', exc_info=True)
            except Exception:
                logger.warning(f'Problem at asset table information {device_raw}', exc_info=True)
            try:
                device.u_business_segment = device_raw.pop(InjectedRawFields.u_business_segment.value, None)
            except Exception:
                logger.warning(f'Problem adding u_business_segment to {device_raw}', exc_info=True)

            snow_nics = device_raw.pop(InjectedRawFields.snow_nics.value, None)
            ci_ip_data = device_raw.pop(InjectedRawFields.ci_ip_data.value, None)
            if isinstance(snow_nics, list):
                if not isinstance(ci_ip_data, list):
                    ci_ip_data = []
                for snow_nic in snow_nics:
                    try:
                        mac_address = snow_nic.get('mac_address')
                        ip_addresses = None
                        if snow_nic.get('ip_address'):
                            ip_addresses = self._parse_raw_snow_ip(snow_nic.get('ip_address'))
                        if mac_address or ip_addresses:
                            device.add_nic(mac=mac_address, ips=ip_addresses, subnets=subnets)

                        try:
                            for ci_ip in ci_ip_data:
                                u_authorative_dns_name = ci_ip.get('u_authorative_dns_name')
                                u_ip_version = ci_ip.get('u_ip_version')
                                u_ip_address = ci_ip.get('u_ip_address')
                                u_lease_contract = ci_ip.get('u_lease_contract')
                                u_netmask = ci_ip.get('u_netmask')
                                u_network_address = ci_ip.get('u_network_address')
                                u_subnet = ci_ip.get('u_subnet')
                                u_zone = ci_ip.get('u_zone')
                                u_ip_address_property = ci_ip.get('u_ip_address_property')
                                u_ip_network_class = ci_ip.get('u_ip_network_class')
                                u_last_discovered = parse_date(ci_ip.get('u_last_discovered'))
                                u_install_status = ci_ip.get('u_install_status')
                                ci_ip_data = CiIpData(u_authorative_dns_name=u_authorative_dns_name,
                                                      u_ip_version=u_ip_version,
                                                      u_ip_address=u_ip_address,
                                                      u_lease_contract=u_lease_contract,
                                                      u_netmask=u_netmask,
                                                      u_network_address=u_network_address,
                                                      u_subnet=u_subnet,
                                                      u_zone=u_zone,
                                                      u_ip_address_property=u_ip_address_property,
                                                      u_ip_network_class=u_ip_network_class,
                                                      u_last_discovered=u_last_discovered,
                                                      u_install_status=u_install_status
                                                      )
                                device.ci_ips.append(ci_ip_data)
                        except Exception:
                            logger.exception(f'Problem getting ci ips table')
                    except Exception:
                        logger.exception(f'Problem with snow nic {snow_nic}')

            snow_ips = device_raw.pop(InjectedRawFields.snow_ips.value, None)
            if isinstance(snow_ips, list):
                for snow_ip in snow_ips:
                    try:
                        device.add_nic(ips=[snow_ip.get('u_address').split(',')[0]], subnets=subnets)
                    except Exception:
                        logger.exception(f'Problem with snow ips {snow_ip}')

            if not install_status or self.__use_ci_table_for_install_status:
                install_status = device_raw.get('install_status')
                if install_status and not isinstance(install_status, str):
                    install_status = install_status_dict.get(install_status)
            if self.__exclude_disposed_devices and install_status \
                    and install_status in ['Disposed', 'Decommissioned']:
                return None
            device.install_status = install_status
            try:
                if (self.__install_status_exclude_list and
                        device_raw.get('install_status') and
                        str(device_raw.get('install_status')) in self.__install_status_exclude_list):

                    return None
            except Exception:
                logger.warning(f'Problem with install status exclude list')

            device.owner = device_raw.pop(InjectedRawFields.owner_name.value, None)
            device.assigned_to = device_raw.get(InjectedRawFields.assigned_to_name.value, None)

            assigned_to_email = device_raw.pop(InjectedRawFields.assigned_to_email.value, None)
            owner_email = device_raw.pop(InjectedRawFields.owner_email.value, None)
            device.email = assigned_to_email or owner_email

            try:
                device.assigned_to_country = device_raw.pop(InjectedRawFields.assigned_to_country.value, None)
                assigned_to_division = device_raw.pop(InjectedRawFields.assigned_to_u_division.value, None)
                if isinstance(assigned_to_division, dict):
                    assigned_to_division = assigned_to_division.get('display_value')
                device.assigned_to_division = assigned_to_division
                assigned_to_business_unit = device_raw.pop(InjectedRawFields.assigned_to_business_unit.value, None)
                if isinstance(assigned_to_business_unit, dict):
                    assigned_to_business_unit = assigned_to_business_unit.get('display_value')
                device.assigned_to_business_unit = assigned_to_business_unit
                device.manager_email = device_raw.pop(InjectedRawFields.manager_email.value, None)
                assigned_to_location = device_raw.pop(InjectedRawFields.assigned_to_location.value, None)
                if isinstance(assigned_to_location, dict):
                    assigned_to_location = assigned_to_location.get('display_value')
                device.assigned_to_location = assigned_to_location
            except Exception:
                logger.exception(f'Problem adding assigned_to to {device_raw}')
            device.u_business_unit = device_raw.pop(InjectedRawFields.u_business_unit.value, None)
            device.device_managed_by = device_raw.pop(InjectedRawFields.device_managed_by.value, None)
            try:
                device.vendor = device_raw.pop(InjectedRawFields.vendor.value, None)
                u_vendor_ban = device_raw.get('u_vendor_ban')
                if isinstance(u_vendor_ban, str):
                    device.u_vendor_ban = u_vendor_ban
                device_manufacturer = device_raw.pop(InjectedRawFields.device_manufacturer.value, None)
                if isinstance(device_manufacturer, dict):
                    device_manufacturer = device_manufacturer.get('display_value')
                device.device_manufacturer = device_manufacturer
                if (device_manufacturer and
                        any(s in device_manufacturer.lower() for s in ['aws', 'amazon']) and
                        (isinstance(device_serial, str) and device_serial.lower().startswith('i-'))):
                    device.cloud_id = device_serial
                    device.cloud_provider = 'AWS'

                cpu_manufacturer = device_raw.pop(InjectedRawFields.cpu_manufacturer.value, None)
                ghz = float_or_none(device_raw.get('cpu_speed'))
                if ghz and isinstance(ghz, float):
                    ghz = ghz / 1024.0
                device.add_cpu(name=device_raw.get('cpu_name'),
                               cores=int_or_none(device_raw.get('cpu_count')),
                               cores_thread=int_or_none(device_raw.get('cpu_core_thread')),
                               ghz=ghz,
                               manufacturer=cpu_manufacturer)
            except Exception:
                logger.debug(f'Problem adding cpu stuff to {device_raw}', exc_info=True)
            try:
                device.company = device_raw.pop(InjectedRawFields.company.value, None)
                device.discovery_source = device_raw.get('discovery_source')
                device.first_discovered = parse_date(device_raw.get('first_discovered'))
                last_discovered = parse_date(device_raw.get('last_discovered'))
                device.last_discovered = last_discovered
                sys_updated_on = parse_date(device_raw.get('sys_updated_on'))
                device.sys_updated_on = sys_updated_on
                if last_discovered and sys_updated_on:
                    device.last_seen = max(sys_updated_on, last_discovered)
                elif last_discovered or sys_updated_on:
                    device.last_seen = last_discovered or sys_updated_on
                if device_raw.get('u_last_seen'):
                    device.last_seen = parse_date(device_raw.get('u_last_seen'))
                device.created_at = parse_date((device_raw.get('sys_created_on')))
                device.created_by = device_raw.get('sys_created_by')
            except Exception:
                logger.exception(f'Problem addding source stuff to {device_raw}')
            try:
                if float_or_none(device_raw.get('disk_space')):
                    device.add_hd(total_size=float_or_none(device_raw.get('disk_space')))
            except Exception:
                logger.exception(f'Problem adding disk stuff to {device_raw}')
            device.u_supplier = device_raw.pop(InjectedRawFields.u_supplier.value, None)
            self._fill_relations(device, device_raw)
            maintenance_dict = device_raw.pop(InjectedRawFields.maintenance_schedule.value, None)
            if isinstance(maintenance_dict, dict):
                self._fill_maintenance_schedule(device, maintenance_dict)
            try:
                device.u_access_authorisers = device_raw.pop(InjectedRawFields.u_access_authorisers.value, None)
                device.u_access_control_list_extraction_method = device_raw.get(
                    'u_access_control_list_extraction_method')
                device.u_acl_contacts = device_raw.pop(InjectedRawFields.u_acl_contacts.value, None)
                device.u_acl_contacts_mailbox = device_raw.get('u_acl_contacts_mailbox')
                device.u_atm_category = device_raw.get('u_atm_category')
                device.u_atm_line_address = device_raw.get('u_atm_line_address')
                device.u_atm_security_carrier = device_raw.get('u_atm_security_carrier')
                device.u_attestation_date = parse_date(device_raw.get('u_attestation_date'))
                device.u_bted_id = device_raw.get('u_bted_id')
                device.u_bucf_contacts = device_raw.pop(InjectedRawFields.u_bucf_contacts.value, None)
                device.u_bucf_contacts_mailbox = device_raw.get('u_bucf_contacts_mailbox')
                device.u_business_owner = device_raw.pop(InjectedRawFields.u_business_owner.value, None)
                device.u_cmdb_data_mgt_journal = device_raw.get('u_cmdb_data_mgt_journal')
                device.u_cmdb_data_owner = device_raw.pop(InjectedRawFields.u_cmdb_data_owner.value, None)
                device.u_cmdb_data_owner_group = device_raw.pop(InjectedRawFields.u_cmdb_data_owner_group.value, None)
                device.u_cmdb_data_owner_team = device_raw.pop(InjectedRawFields.u_cmdb_data_owner_team.value, None)
                device.u_cmdb_data_steward = device_raw.pop(InjectedRawFields.u_cmdb_data_steward.value, None)
                device.u_custodian = device_raw.pop(InjectedRawFields.u_custodian.value, None)
                device.u_custodian_group = device_raw.pop(InjectedRawFields.u_custodian_group.value, None)
                device.u_custodian_team = device_raw.get('u_custodian_team')
                device.u_delivery_of_access_control_list = device_raw.get('u_delivery_of_access_control_list')
                device.u_fulfilment_group = device_raw.pop(InjectedRawFields.u_fulfilment_group.value, None)
                device.u_last_update_from_import = device_raw.get('u_last_update_from_import')
                device.u_oim_division = device_raw.get('u_oim_division')
                device.u_organisation = device_raw.get('u_organisation')
                device.u_orphan_account_contacts = device_raw.pop(
                    InjectedRawFields.u_orphan_account_contacts.value, None)
                device.u_orphan_account_manager = device_raw.pop(InjectedRawFields.u_orphan_account_manager.value, None)
                device.u_permitted_childless = device_raw.get('u_permitted_childless')
                device.u_permitted_parentless = device_raw.get('u_permitted_parentless')
                device.u_primary_support_group = device_raw.pop(InjectedRawFields.u_primary_support_group.value, None)
                device.u_primary_support_sme = device_raw.pop(InjectedRawFields.u_primary_support_sme.value, None)
                device.u_primary_support_team = device_raw.get('u_primary_support_team')
                device.u_reason_for_childless = device_raw.get('u_reason_for_childless')
                device.u_reason_for_parentless = device_raw.get('u_reason_for_parentless')
                device.u_recertification_approach = device_raw.get('u_recertification_approach')
                device.u_recertification_contacts = device_raw.pop(InjectedRawFields.u_recertification_contacts.value,
                                                                   None)
                device.u_recertification_type = device_raw.get('u_recertification_type')
                device.u_record_date_time = device_raw.get('u_record_date_time')
                device.u_record_id = device_raw.get('u_record_id')
                device.u_record_name = device_raw.get('u_record_name')
                device.u_ref_1_label = device_raw.get('u_ref_1_label')
                device.u_ref_1_value = device_raw.get('u_ref_1_value')
                device.u_ref_2_label = device_raw.get('u_ref_2_label')
                device.u_ref_2_value = device_raw.get('u_ref_2_value')
                device.u_ref_3_label = device_raw.get('u_ref_3_label')
                device.u_ref_3_value = device_raw.get('u_ref_3_value')
                device.u_role = device_raw.get('u_role')
                device.u_security_administrators = device_raw.pop(InjectedRawFields.u_security_administrators.value,
                                                                  None)
                device.u_si_id = device_raw.get('u_si_id')
                device.u_source_name = device_raw.get('u_source_name')
                device.u_source_target_class = device_raw.get('u_source_target_class')
                device.u_sox_control = device_raw.get('u_sox_control')
                device.u_suspensions_deletions = device_raw.get('u_suspensions_deletions')
                device.u_technical_admin_contacts = device_raw.pop(InjectedRawFields.u_technical_admin_contacts.value,
                                                                   None)
                device.u_tech_admin_mailbox = device_raw.get('u_tech_admin_mailbox')
                device.u_toxic_division_group = device_raw.pop(InjectedRawFields.u_toxic_division_group.value, None)
                device.u_uar_contacts = device_raw.pop(InjectedRawFields.u_uar_contacts.value, None)
                device.u_uar_contacts_mailbox = device_raw.get('u_uar_contacts_mailbox')
                device.u_uav_delegates = device_raw.pop(InjectedRawFields.u_uav_delegates.value, None)
                device.u_work_notes = device_raw.get('u_work_notes')
            except Exception:
                logger.exception(f'Failed parsing cmdb_ci_computer_atm fields')
            try:
                device.phone_number = device_raw.get('phone_number')
                device.ci_comm_type = device_raw.get('type')
            except Exception:
                logger.exception(f'failed parsing cmdb_ci_comm fields')
            try:
                device.u_it_owner_organization = device_raw.pop(InjectedRawFields.u_it_owner_organization.value, None)
                device.u_managed_by_vendor = device_raw.pop(InjectedRawFields.u_managed_by_vendor.value, None)
            except Exception:
                logger.exception(f'failed parsing it_owner_org / managed_by_vendor')
            try:
                device.u_division = device_raw.pop(InjectedRawFields.u_division.value, None)
                device.u_level1_mgmt_org_code = device_raw.pop(InjectedRawFields.u_level1_mgmt_org_code.value, None)
                device.u_level2_mgmt_org_code = device_raw.pop(InjectedRawFields.u_level2_mgmt_org_code.value, None)
                device.u_level3_mgmt_org_code = device_raw.pop(InjectedRawFields.u_level3_mgmt_org_code.value, None)
                device.u_pg_email_address = device_raw.pop(InjectedRawFields.u_pg_email_address.value, None)
            except Exception:
                logger.exception(f'failed parsing levelx_mgmt fields')
            try:
                device.u_employee_type = device_raw.get('u_employee_type')
                device.u_job_function = device_raw.get('u_job_function')
                device.u_legal_entity_name = device_raw.get('u_legal_entity_name')
                device.u_organization_segment = device_raw.get('u_organization_segment')
                device.u_sub_organization_segment = device_raw.get('u_sub_organization_segment')
                device.u_labor_model = device_raw.get('u_labor_model')
                device.u_parent_organization_name = device_raw.get('u_parent_organization_name')
                device.u_organization_name = device_raw.get('u_organization_name')
                device.u_organization_id = device_raw.get('u_organization_id')
            except Exception:
                logger.exception(f'failed parsing u_labor_model fields')
            device.domain = device_raw.get('dns_domain') or device_raw.get('os_domain')
            device.used_for = device_raw.get('used_for')
            device.tenable_asset_group = device_raw.get('u_tenable_asset_group')
            u_environment = device_raw.get('u_environment')
            device.environment = consts.U_ENVIRONMENT_DICT.get(str(u_environment)) or u_environment
            device.cmdb_business_function = device_raw.get('u_cmdb_business_function')
            device.management_ip = device_raw.get('u_management_ip')
            device.end_of_support = device_raw.get('u_end_of_support')
            device.firmware_version = device_raw.get('u_firmware_version')
            device.model_version_number = device_raw.get('u_model_version_number')
            if self.__fetch_operational_status:
                operational_status = device_raw.get('operational_status')
                if operational_status and not isinstance(operational_status, str):
                    operational_status = operational_status_dict.get(operational_status)
                if operational_status_dict is consts.INSTALL_STATUS_DICT:
                    # if no explicit operational_status_dict given, try to use a display value if exists
                    operational_status = device_raw.get('dv_operational_status') or operational_status
                device.operational_status = operational_status
            device.hardware_status = device_raw.get('hardware_status')
            hardware_sub_status = device_raw.get('hardware_substatus')
            if isinstance(hardware_sub_status, str):
                device.hardware_substatus = hardware_sub_status
            device.u_number = device_raw.get('u_number')
            device.u_consumption_type = device_raw.get('u_consumption_type')
            u_function = device_raw.get('u_function')
            if isinstance(u_function, dict):
                u_function = u_function.get('display_value')
            device.u_function = u_function
            device.u_ge_data_class = device_raw.get('u_ge_data_class')
            device.u_location_details = device_raw.get('u_location_details')

            management_access_address = device_raw.get('u_management_access_address')
            if management_access_address:
                device.u_management_access_address = management_access_address

            device.u_management_access_type = device_raw.get('u_management_access_type')
            device.u_network_zone = device_raw.get('u_network_zone')

            try:
                verification_install_status = device_raw.get(InjectedRawFields.verification_status.value, None)
                if (verification_install_status and
                        not isinstance(verification_install_status, str) and
                        verification_install_status_dict):
                    verification_install_status = verification_install_status_dict.get(verification_install_status)
                device.verification_install_status = verification_install_status

                verification_operational_status = device_raw.get(
                    InjectedRawFields.verification_operational_status.value, None)
                if (verification_operational_status and
                        not isinstance(verification_operational_status, str) and
                        verification_operational_status_dict):
                    verification_operational_status = verification_operational_status_dict.get(
                        verification_operational_status)
                device.verification_operational_status = verification_operational_status
            except Exception:
                logger.warning(f'Failed setting verification table fields', exc_info=True)

            device_compliance_exceptions = device_raw.pop(InjectedRawFields.compliance_exceptions.value, None)
            if isinstance(device_compliance_exceptions, list):
                for compliance_exception_data in device_compliance_exceptions:
                    try:
                        if not (isinstance(compliance_exception_data, dict) and
                                isinstance(compliance_exception_data.get('active'), str)):
                            logger.warning(f'Failed to locate or Invalid compliance exception dict:'
                                           f' {compliance_exception_data}')
                            continue

                        # we only parse active exceptions
                        if compliance_exception_data.get('active') != 'true':
                            logger.debug(f'Skipping inactive compliance exception: {compliance_exception_data}')
                            continue

                        device_compliance_exceptions.append(SnowComplianceException(
                            exception_id=compliance_exception_data.get('number'),
                            policy_name=compliance_exception_data.get('policy.name'),
                            policy_statement=compliance_exception_data.get('policy_statement.name'),
                            issue=compliance_exception_data.get('issue'),
                            opened_by=compliance_exception_data.get('opened_by.name'),
                            short_description=compliance_exception_data.get('short_description'),
                            state=compliance_exception_data.get('state'),
                            substate=compliance_exception_data.get('substate'),
                            valid_to=parse_date(compliance_exception_data.get('valid_to')),
                            assignment_group=compliance_exception_data.get('assignment_group.name'),
                        ))
                    except Exception:
                        logger.warning(f'Failed parsing compliance exception: {compliance_exception_data}')

                device.compliance_exceptions = device_compliance_exceptions

            # Note - explicit '.pop' for removing large dicts for device_raw
            device_software_list = device_raw.pop(InjectedRawFields.snow_software.value, None)
            if isinstance(device_software_list, list):
                for soft_dict in device_software_list:
                    if not isinstance(soft_dict, dict):
                        continue
                    try:
                        device.add_installed_software(
                            name=(soft_dict.get('software.name') or  # NON-SAM
                                  soft_dict.get('display_name')),  # SAM
                            version=(soft_dict.get('software.version') or  # NON-SAM
                                     soft_dict.get('version')),  # SAM
                            vendor=soft_dict.get('software.vendor.name'),  # NON-SAM
                            publisher=(soft_dict.get('software.manufacturer.name') or  # NON-SAM
                                       soft_dict.get('publisher')),  # SAM
                        )
                    except Exception:
                        pass

            device_contracts_raw = device_raw.pop(InjectedRawFields.contracts.value, None)
            if isinstance(device_contracts_raw, list):
                for contract_dict in device_contracts_raw:
                    if not (isinstance(contract_dict, dict) and contract_dict.get('contract.parent.number')):
                        continue
                    try:
                        parent_number = contract_dict.get('contract.parent.number')
                        contract = SnowDeviceContract(
                            number=contract_dict.get('contract.number'),
                            short_desc=contract_dict.get('contract.short_description'),
                            parent_number=parent_number,
                        )

                        if (isinstance(self._contract_parent_numbers, str) and
                                isinstance(parent_number, str) and
                                parent_number.lower() in self._contract_parent_numbers.lower().split(',')):

                            device.contracts.append(contract)

                        elif (isinstance(self._diversiture_contract_parent_numbers, str) and
                              isinstance(parent_number, str) and
                              parent_number.lower() in self._diversiture_contract_parent_numbers.lower().split(',')):

                            device.diversiture_contracts.append(contract)
                    except Exception:
                        logger.debug(f'failed appending contract: {contract_dict}', exc_info=True)

            device.set_raw(device_raw)
            if not got_serial and not got_nic and self.__exclude_no_strong_identifier:
                return None
            return device
        except Exception:
            logger.exception(f'Problem with fetching ServiceNow Device {device_raw}')
            return None

    def _get_config_enum_from_file(self, file_config):

        if not file_config:
            return None

        result_dict = dict()
        try:
            csv_data_bytes = self._grab_file_contents(file_config)
            encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
            encoding = encoding or 'utf-8'
            csv_data = csv_data_bytes.decode(encoding)
            csv_data = make_dict_from_csv(csv_data)
            if 'Value' in csv_data.fieldnames and 'Label' in csv_data.fieldnames:
                for csv_line in csv_data:
                    if csv_line.get('Value') and csv_line.get('Label'):
                        result_dict[str(csv_line['Value'])] = csv_line['Label']
        except Exception:
            logger.exception(f'Problem parsing config enum - {file_config}')

        return result_dict

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific ServiceNow domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a ServiceNow connection

        :return: A json with all the attributes returned from the ServiceNow Server
        """

        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    generic_service_now_query_devices_by_client,
                    (
                        client_data,
                    ),
                    {}
                )
            ],
            1
        ))
        # To restore original method:
        # yield from generic_service_now_query_devices_by_client(client_data)

    def _query_users_by_client(self, key, data):
        if not self.__fetch_users:
            return
        _ = (yield from concurrent_multiprocess_yield(
            [
                (
                    generic_service_now_query_users_by_client,
                    (
                        data,
                    ),
                    {}
                )
            ],
            1
        ))
        # To restore original method:
        # yield from generic_service_now_query_users_by_client(data)

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, raw_data):
        for user_raw in raw_data:
            try:
                try:
                    if self._use_exclusion_field and parse_bool_from_raw(user_raw.get('u_exclude_from_discovery')):
                        logger.debug(f'ignoring excluded user {user_raw.get("sys_id")}')
                        continue
                except Exception:
                    logger.warning(f'Failed handling exclusion of user')
                user = self._new_user_adapter()
                sys_id = user_raw.get('sys_id')
                if not sys_id:
                    logger.warning(f'Bad user with no id {user_raw}')
                    continue
                user.id = sys_id
                found_whitelist = False
                mail = user_raw.get('email') or user_raw.get('u_pg_email_address')
                if self.__email_whitelist:
                    for whielist_mail in self.__email_whitelist:
                        if whielist_mail in mail:
                            found_whitelist = True
                    if not found_whitelist:
                        continue
                user.mail = mail
                user.employee_number = user_raw.get('employee_number')
                user.user_country = user_raw.get('country')
                user.first_name = user_raw.get('first_name')
                active = user_raw.get('active')
                if self.__fetch_only_active_users and active != 'true':
                    continue
                user.active = active
                user.last_name = user_raw.get('last_name')
                user.username = user_raw.get('name')
                updated_on = parse_date(user_raw.get('sys_updated_on'))
                user.updated_on = updated_on
                user.user_created = parse_date(user_raw.get('sys_created_on'))
                last_logon = parse_date(user_raw.get('last_login_time'))
                user.last_logon = last_logon
                try:
                    if last_logon and updated_on:
                        user.last_seen = max(last_logon, updated_on)
                    elif last_logon or updated_on:
                        user.last_seen = last_logon or updated_on
                except Exception:
                    logger.exception(f'Problem getting last seen for {user_raw}')
                user.user_title = user_raw.get('title') or user_raw.get('u_playtika_title')
                try:
                    user.user_manager = get_reference_display_value(user_raw.get('manager'))
                except Exception:
                    logger.warning(f'Problem getting manager for {user_raw}', exc_info=True)
                user.snow_source = user_raw.get('source')
                user.snow_roles = user_raw.get('roles')
                user.user_telephone_number = user_raw.get('phone')
                saved_groups = user_raw.get('u_saved_groups')
                if isinstance(saved_groups, str):
                    user.u_saved_groups = saved_groups.split(',')
                saved_roles = user_raw.get('u_saved_roles')
                if isinstance(saved_roles, str):
                    user.u_saved_roles = saved_roles.split(',')
                user.u_studio = user_raw.get('u_studio')
                user.u_sub_department = user_raw.get('u_sub_department')
                user.u_profession = user_raw.get('u_profession')
                user.u_company = user_raw.pop(InjectedRawFields.u_company.value, None)
                user.u_department = user_raw.pop(InjectedRawFields.u_department.value, None)
                if user_raw.get('vip'):
                    user.u_vip = (user_raw.get('vip') == 'true')
                user.u_business_unit = user_raw.get('u_business_unit')
                user.u_division = user_raw.get('u_division')
                user.u_level1_mgmt_org_code = user_raw.get('u_level1_mgmt_org_code')
                user.u_level2_mgmt_org_code = user_raw.get('u_level2_mgmt_org_code')
                user.u_level3_mgmt_org_code = user_raw.get('u_level3_mgmt_org_code')
                user.u_pg_email_address = user_raw.get('u_pg_email_address')
                user.set_raw(user_raw)
                yield user
            except Exception:
                logger.warning(f'Problem getting user {user_raw}', exc_info=True)

    @staticmethod
    def _fill_relations(device, device_raw) -> Optional[List[dict]]:
        relations_raw = device_raw.pop(InjectedRawFields.relations.value, None)
        if not isinstance(relations_raw, dict):
            return

        # pylint: disable=no-else-return
        def _get_node_class(depth):
            if depth == 2:
                return RelativeInformationNode1
            else:
                return RelativeInformationLeaf

        def _parse_relatives(curr_relatives_raw, depth, is_downstream):
            if not isinstance(curr_relatives_raw, list):
                return None
            curr_relative_objs = []
            for relative_sys_id in curr_relatives_raw:
                relative_obj = _recursive_prepare_relation_node(relative_sys_id,
                                                                depth=depth - 1,
                                                                is_downstream=is_downstream)
                if not relative_obj:
                    continue
                curr_relative_objs.append(relative_obj)
            return curr_relative_objs

        def _recursive_prepare_relation_node(curr_relation: dict, depth, is_downstream=False):
            curr_node_cls = _get_node_class(depth)
            curr_node = curr_node_cls(name=curr_relation.get('name'),
                                      sys_class_name=curr_relation.get('sys_class_name'))

            # Recursion explicit stop - last depth should not have relatives
            if depth == 1:
                return curr_node

            # Note: the actual recursion occurs here
            #       _recursive_prepare_relation_node -> _parse_relations -> _recursive_prepare_relation_node
            # Recursion implicit stop - no relatives, no recursion :)
            if is_downstream:
                curr_node.downstream = _parse_relatives(curr_relation.get(consts.RELATIONS_TABLE_CHILD_KEY),
                                                        depth,
                                                        is_downstream)
            else:
                curr_node.upstream = _parse_relatives(curr_relation.get(consts.RELATIONS_TABLE_PARENT_KEY),
                                                      depth,
                                                      is_downstream)
            return curr_node

        try:
            # Note: we consider the current device as MAX_DEPTH, its relations begin at MAX_DEPTH-1
            downstream_raw_list = relations_raw.get(consts.RELATIONS_TABLE_CHILD_KEY)
            if isinstance(downstream_raw_list, list):
                device.downstream = [_recursive_prepare_relation_node(downstream_raw, consts.MAX_RELATIONS_DEPTH - 1,
                                                                      is_downstream=True)
                                     for downstream_raw in downstream_raw_list]
            upstream_raw_list = relations_raw.get(consts.RELATIONS_TABLE_PARENT_KEY)
            if isinstance(upstream_raw_list, list):
                device.upstream = [_recursive_prepare_relation_node(upstream_raw, consts.MAX_RELATIONS_DEPTH - 1,
                                                                    is_downstream=False)
                                   for upstream_raw in upstream_raw_list]

        except Exception:
            logger.exception(f'Failed parsing relations')

    @staticmethod
    def _fill_maintenance_schedule(device, maintenance_schedule_dict):
        try:
            maintenance_schedule = MaintenanceSchedule()
            maintenance_schedule.name = maintenance_schedule_dict.get('name')
            maintenance_schedule.ms_type = maintenance_schedule_dict.get('type')
            maintenance_schedule.description = maintenance_schedule_dict.get('description')
            maintenance_schedule.document = maintenance_schedule_dict.get('document')
            maintenance_schedule.document_key = maintenance_schedule_dict.get('document_key')
            device.maintenance_schedule = maintenance_schedule
        except Exception:
            logger.warning(f'Problem adding maintenance schedule to {maintenance_schedule_dict}', exc_info=True)

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self.create_snow_device(device_raw=device_raw,
                                             fetch_ips=self.__fetch_ips)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    #pylint: disable=no-self-use
    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True

    def _on_config_update(self, config):
        # config.get('parallel_requests') must be injected to config BEFORE this call for parallel restriction

        logger.info(f'Loading Snow config: {config}')
        self.__fetch_users = config['fetch_users']
        self.__fetch_ips = config['fetch_ips']
        self.__fetch_users_info_for_devices = config['fetch_users_info_for_devices']
        self.__exclude_disposed_devices = config['exclude_disposed_devices']
        self.__exclude_no_strong_identifier = config['exclude_no_strong_identifier']
        self.__use_ci_table_for_install_status = config['use_ci_table_for_install_status']
        self.__exclude_vm_tables = config['exclude_vm_tables']
        self.__fetch_operational_status = config.get('fetch_operational_status')
        self.__fetch_only_virtual_devices = config.get('fetch_only_virtual_devices') or False
        self.__email_whitelist = config['email_whitelist'].split(',') if config.get('email_whitelist') else None
        self.__fetch_only_active_users = config.get('fetch_only_active_users') or False
        self.__install_status_exclude_list = config.get('install_status_exclude_list').split(',') \
            if config.get('install_status_exclude_list') else None
        self.__fetch_ci_relations = config['fetch_ci_relations']
        self.__when_no_hostname_fallback_to_name = config.get('when_no_hostname_fallback_to_name') or False
        self._fetch_compliance_exceptions = config['fetch_compliance_exceptions']
        self._use_exclusion_field = config['use_exclusion_field']
        self._is_ram_in_gb = config.get('is_ram_in_gb') or False
        self._fetch_software_product_model = config.get('fetch_software_product_model') or False
        self._fetch_cmdb_model = config.get('fetch_cmdb_model') or False
        self._fetch_business_unit_dict = config.get('fetch_business_unit_dict') or False
        self._fetch_installed_software = config.get('fetch_installed_software') or False
        self._fetch_nics_table = config['fetch_nics_table'] if 'fetch_nics_table' in config else True
        self._contract_parent_numbers: Optional[str] = config.get('contract_parent_numbers')
        self._diversiture_contract_parent_numbers: Optional[str] = config.get('diversiture_contract_parent_numbers')
        self._use_dotwalking = bool(config.get('use_dotwalking'))
        self._dotwalking_per_request_limit = config.get('dotwalking_per_request_limit') or \
            consts.DEFAULT_DOTWALKING_PER_REQUEST
        self._use_cached_users = bool(config.get('use_cached_users'))

        self._snow_last_updated_threashold = None
        last_updated = config.get('snow_last_updated')
        if isinstance(last_updated, int) and last_updated > 0:
            self._snow_last_updated_threashold = timedelta(hours=last_updated)

        self._snow_user_last_created_threashold = None
        snow_user_last_created = config.get('snow_user_last_created')
        if isinstance(snow_user_last_created, int) and snow_user_last_created > 0:
            self._snow_user_last_created_threashold = timedelta(hours=snow_user_last_created)

        self.__parallel_requests = config.get('parallel_requests') or consts.DEFAULT_ASYNC_CHUNK_SIZE
