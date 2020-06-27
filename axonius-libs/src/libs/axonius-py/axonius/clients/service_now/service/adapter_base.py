import logging
import re
from abc import abstractmethod
from typing import Optional, List

import chardet

from axonius.adapter_base import AdapterProperty, AdapterBase
from axonius.clients.service_now import consts
from axonius.clients.service_now.service.structures import RelativeInformationNode1, RelativeInformationLeaf, \
    MaintenanceSchedule, CiIpData
from axonius.utils.datetime import parse_date
from axonius.utils.parsing import make_dict_from_csv

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=invalid-name,too-many-nested-blocks,too-many-arguments,too-many-instance-attributes
# pylint: disable=too-many-return-statements


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
            'title': 'Use CMDB_CI table instead of ALM ASSET table for install status',
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
    ]
    SERVICE_NOW_DB_CONFIG_SCHEMA_REQUIRED = [
        'fetch_users',
        'fetch_ips', 'use_ci_table_for_install_status',
        'exclude_disposed_devices',
        'fetch_users_info_for_devices',
        'exclude_no_strong_identifier',
        'exclude_vm_tables',
        'fetch_only_active_users',
        'fetch_only_virtual_devices',
        'fetch_operational_status',
        'fetch_ci_relations',
    ]
    SERVICE_NOW_DB_CONFIG_DEFAULT = {
        'fetch_users': True,
        'fetch_ips': True,
        'fetch_users_info_for_devices': True,
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
    }

    @abstractmethod
    def get_connection(self, client_config):
        pass

    def _connect_client(self, client_config):
        return (self.get_connection(client_config),
                self._get_config_enum_from_file(client_config.get('install_status_file')),
                self._get_config_enum_from_file(client_config.get('operational_status_file')))

    @classmethod
    def _get_optional_raw_reference(cls, device_raw: dict, field_name: str):
        if not (isinstance(device_raw, dict) and isinstance(field_name, str)):
            return None
        raw_value = device_raw.get(field_name)
        if not raw_value:
            return None
        return raw_value

    @classmethod
    def _parse_optional_reference(cls, device_raw: dict, field_name: str, reference_table: dict):
        raw_reference = cls._get_optional_raw_reference(device_raw, field_name)
        if not isinstance(raw_reference, dict):
            return raw_reference
        return reference_table.get(raw_reference.get('value'))

    @classmethod
    def _parse_optional_reference_value(cls, device_raw: dict, field_name: str,
                                        reference_table: dict, reference_table_field: str):
        raw_value = cls._parse_optional_reference(device_raw, field_name, reference_table)
        if not isinstance(raw_value, dict):
            return None
        return raw_value.get(reference_table_field)

    # pylint: disable=R0912,R0915,R0914
    def create_snow_device(self,
                           device_raw,
                           table_type=None,
                           snow_location_table_dict=None,
                           fetch_ips=True,
                           snow_department_table_dict=None,
                           users_table_dict=None,
                           snow_nics_table_dict=None,
                           users_username_dict=None,
                           ci_ips_table_dict=None,
                           snow_alm_asset_table_dict=None,
                           snow_user_groups_table_dict=None,
                           companies_table_dict=None,
                           ips_table_dict=None,
                           install_status_dict=None,
                           supplier_table_dict=None,
                           relations_table_dict=None,
                           relations_info_dict=None,
                           snow_software_product_table_dict=None,
                           snow_maintenance_sched_dict=None,
                           snow_model_dict=None,
                           snow_logicalci_dict=None,
                           operational_status_dict=None):
        got_nic = False
        got_serial = False
        if not install_status_dict:
            install_status_dict = consts.INSTALL_STATUS_DICT
        if not operational_status_dict:
            operational_status_dict = consts.INSTALL_STATUS_DICT
        if ci_ips_table_dict is None:
            ci_ips_table_dict = dict()
        if users_username_dict is None:
            users_username_dict = dict()
        if snow_user_groups_table_dict is None:
            snow_user_groups_table_dict = dict()
        if companies_table_dict is None:
            companies_table_dict = dict()
        if snow_location_table_dict is None:
            snow_location_table_dict = dict()
        if snow_nics_table_dict is None:
            snow_nics_table_dict = dict()
        if ips_table_dict is None:
            ips_table_dict = dict()
        if snow_alm_asset_table_dict is None:
            snow_alm_asset_table_dict = dict()
        if users_table_dict is None:
            users_table_dict = dict()
        if snow_department_table_dict is None:
            snow_department_table_dict = dict()
        if supplier_table_dict is None:
            supplier_table_dict = dict()
        if relations_table_dict is None:
            relations_table_dict = dict()
        if relations_info_dict is None:
            relations_info_dict = dict()
        if snow_software_product_table_dict is None:
            snow_software_product_table_dict = dict()
        if snow_maintenance_sched_dict is None:
            snow_maintenance_sched_dict = dict()
        if snow_model_dict is None:
            snow_model_dict = dict()
        if snow_logicalci_dict is None:
            snow_logicalci_dict = dict()
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('sys_id')
            if not device_id:
                logger.warning(f'Problem getting id at {device_raw}')
                return None
            device.id = str(device_id)
            device.table_type = table_type
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
            try:
                ip_addresses = device_raw.get('ip_address')
                if fetch_ips and ip_addresses and not any(elem in ip_addresses for elem in ['DHCP',
                                                                                            '*',
                                                                                            'Stack',
                                                                                            'x',
                                                                                            'X']):
                    if '/' in ip_addresses:
                        ip_addresses = ip_addresses.split('/')
                    elif ',' in ip_addresses:
                        ip_addresses = ip_addresses.split(',')
                    elif ';' in ip_addresses:
                        ip_addresses = ip_addresses.split(';')
                    elif '&' in ip_addresses:
                        ip_addresses = ip_addresses.split('&')
                    elif 'and' in ip_addresses:
                        ip_addresses = ip_addresses.split('and')
                    elif r'\\\\' in ip_addresses:
                        # Example: 1.1.1.1\\\\1.1.1.1
                        ip_addresses = ip_addresses.split(r'\\\\')
                    elif re.search(consts.RE_SQUARED_BRACKET_WRAPPED, ip_addresses):
                        # Example: [1.1.1.1] or [1.1.1.1][255.255.255.192]
                        # Note: all of the use cases ive seen had only one ip (and at most an additional subnet),
                        #       This implementation considers both as IPs in case this will actually be the case,
                        #       at most the subnet will be ignored as invalid ip
                        ip_addresses = re.findall(consts.RE_SQUARED_BRACKET_WRAPPED, ip_addresses)
                    elif ':' in ip_addresses:
                        # Example: 1.1.1.1:8000
                        ip_addresses = [ip_addresses.split(':')[0]]
                    elif '(ilo' in ip_addresses.lower():
                        # Example: 1.1.1.1 (iLo 1.1.1.1) or 1.1.1.1 (iLo)
                        ip_addresses = [ip_addresses.split('(i', 1)[0]]
                    elif '-' in ip_addresses:
                        # Example: 1.1.1.1 - VLAN2
                        ip_addresses = [ip_addresses.split('-')[0]]
                    else:
                        ip_addresses = [ip_addresses]
                    ip_addresses = [ip.strip() for ip in ip_addresses]
                else:
                    ip_addresses = None
                mac_address = device_raw.get('mac_address')
                if mac_address or ip_addresses:
                    got_nic = True
                    device.add_nic(mac_address, ip_addresses)
            except Exception:
                logger.warning(f'Problem getting NIC at {device_raw}', exc_info=True)
            try:
                # Parse support_group
                # Some clients have support_group through u_cmdb_ci_logicalci table
                snow_logicalci_value = \
                    self._parse_optional_reference(device_raw, 'u_logical_ci', snow_logicalci_dict) or {}

                device.support_group = (
                    self._parse_optional_reference_value(device_raw, 'support_group',
                                                         snow_user_groups_table_dict, 'name') or
                    self._parse_optional_reference_value(snow_logicalci_value, 'support_group',
                                                         snow_user_groups_table_dict, 'name'))

                snow_support_group_value = (self._parse_optional_reference(device_raw, 'support_group',
                                                                           snow_user_groups_table_dict) or
                                            self._parse_optional_reference(snow_logicalci_value, 'support_group',
                                                                           snow_user_groups_table_dict))
                if isinstance(snow_support_group_value, dict):
                    device.u_director = self._parse_optional_reference_value(snow_support_group_value, 'u_director',
                                                                             users_table_dict, 'name')
                    device.u_manager = self._parse_optional_reference_value(snow_support_group_value, 'u_manager',
                                                                            users_table_dict, 'name')
            except Exception:
                logger.warning(f'Problem adding support group to {device_raw}', exc_info=True)

            try:
                mac_u = device_raw.get('u_mac_address')
                if mac_u:
                    device.add_nic(mac=mac_u)
            except Exception:
                logger.exception(f'Problem getting mac 2 for {device_raw}')

            os_title = device_raw.get('os')
            u_operating_system = self._parse_optional_reference(device_raw, 'u_operating_system',
                                                                snow_software_product_table_dict)
            if isinstance(u_operating_system, dict):
                software_product = u_operating_system or {}
                os_title = os_title or software_product.get('title')
                # Take new fields and add them
                u_operating_system = (f'{software_product.get("major_version") or ""}'
                                      f'.{software_product.get("major_version") or ""}'
                                      f' {software_product.get("build_version") or ""}')
            if u_operating_system and not isinstance(u_operating_system, str):
                logger.warning(f'Unknown non-empty u_operating_system type: {u_operating_system}')
                u_operating_system = ''

            device.figure_os(' '.join([os_title or '',
                                       (device_raw.get('os_address_width') or ''),
                                       (u_operating_system or ''),
                                       (device_raw.get('os_domain') or ''),
                                       (device_raw.get('os_service_pack') or ''),
                                       (device_raw.get('os_version') or '')]))
            device.os.install_date = parse_date(device_raw.get('install_date'))
            device_model = None
            curr_model_dict = self._parse_optional_reference(device_raw, 'model_id', snow_model_dict) or {}
            try:
                model_u_classification = curr_model_dict.get('u_classification')
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
                logger.warning(f'Problem getting model classification at {curr_model_dict}', exc_info=True)
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
            try:
                device.device_model = (self._get_optional_raw_reference(device_raw, 'model_number') or
                                       self._parse_optional_reference_value(device_raw, 'model_id',
                                                                            snow_model_dict, 'name') or
                                       curr_model_dict.get('display_name'))
            except Exception:
                logger.warning(f'Problem getting model at {device_raw}', exc_info=True)
            try:
                device_serial = device_raw.get('serial_number') or ''
                if (device_serial or '').startswith('VMware'):
                    device_serial += device_model or ''
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
                ram_mb = device_raw.get('ram', '')
                if ram_mb != '' and ram_mb != '-1' and ram_mb != -1:
                    device.total_physical_memory = int(ram_mb) / 1024.0
            except Exception:
                logger.warning(f'Problem getting ram at {device_raw}', exc_info=True)
            try:
                alias = device_raw.get('u_alias')
                device.u_alias = alias
                host_name = device_raw.get('host_name') or device_raw.get('fqdn') or device_raw.get('u_fqdn')
                if host_name and name and name.lower() in host_name.lower():
                    device.hostname = host_name.split('.')[0].strip()
                else:
                    if alias and ',' in alias and '|' in name:
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
            try:
                device.snow_department = self._parse_optional_reference_value(device_raw, 'department',
                                                                              snow_department_table_dict, 'name')
            except Exception:
                logger.warning(f'Problem adding assigned_to to {device_raw}', exc_info=True)
            try:
                device.physical_location = self._parse_optional_reference_value(device_raw, 'location',
                                                                                snow_location_table_dict, 'name')
            except Exception:
                logger.warning(f'Problem adding assigned_to to {device_raw}', exc_info=True)
            try:
                snow_asset = self._parse_optional_reference(device_raw, 'asset', snow_alm_asset_table_dict) or {}
                install_status = None
                if snow_asset:
                    try:
                        install_status = install_status_dict.get(snow_asset.get('install_status'))
                    except Exception:
                        logger.warning(f'Problem getting install status for {device_raw}', exc_info=True)
                    device.u_loaner = snow_asset.get('u_loaner')
                    device.u_shared = snow_asset.get('u_shared')
                    try:
                        device.first_deployed = parse_date(snow_asset.get('u_first_deployed'))
                    except Exception:
                        logger.warning(f'Problem getting first deployed at {device_raw}', exc_info=True)
                    device.u_altiris_status = snow_asset.get('u_altiris_status')
                    device.u_casper_status = snow_asset.get('u_casper_status')
                    try:
                        device.substatus = snow_asset.get('substatus')
                    except Exception:
                        logger.warning(f'Problem adding hardware status to {device_raw}', exc_info=True)
                    try:
                        device.purchase_date = parse_date(snow_asset.get('purchase_date'))
                    except Exception:
                        logger.warning(f'Problem adding purchase date to {device_raw}', exc_info=True)
                    try:
                        device.snow_location = self._parse_optional_reference_value(snow_asset, 'location',
                                                                                    snow_location_table_dict, 'name')
                    except Exception:
                        logger.warning(f'Problem adding assigned_to to {device_raw}', exc_info=True)
                    try:
                        device.u_business_segment = self._parse_optional_reference_value(
                            device_raw, 'u_business_segment', snow_department_table_dict, 'name')
                    except Exception:
                        logger.warning(f'Problem adding u_business_segment to {device_raw}', exc_info=True)

                    try:
                        snow_nics = snow_nics_table_dict.get(device_raw.get('sys_id'))
                        if isinstance(snow_nics, list):
                            for snow_nic in snow_nics:
                                try:
                                    device.add_nic(mac=snow_nic.get('mac_address'), ips=[snow_nic.get('ip_address')])
                                    try:
                                        ci_ip_data = ci_ips_table_dict.get(snow_nic.get('correlation_id'))
                                        if not isinstance(ci_ip_data, list):
                                            ci_ip_data = []

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
                    except Exception:
                        logger.warning(f'Problem adding assigned_to to {device_raw}', exc_info=True)
                try:
                    snow_ips = ips_table_dict.get(device_raw.get('sys_id'))
                    if isinstance(snow_ips, list):
                        for snow_ip in snow_ips:
                            try:
                                device.add_nic(ips=[snow_ip.get('u_address').split(',')[0]])
                            except Exception:
                                logger.exception(f'Problem with snow ips {snow_ip}')
                except Exception:
                    logger.warning(f'Problem adding assigned_to to {device_raw}', exc_info=True)
                if not install_status or self.__use_ci_table_for_install_status:
                    install_status = install_status_dict.get(device_raw.get('install_status'))
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
            except Exception:
                logger.warning(f'Problem at asset table information {device_raw}', exc_info=True)

            device.owner = self._parse_optional_reference_value(device_raw, 'owned_by', users_table_dict, 'name')
            owned_by = self._parse_optional_reference(device_raw, 'owned_by', users_table_dict) or {}
            if isinstance(owned_by, dict) and owned_by.get('email'):
                device.email = owned_by.get('email')

            try:
                device.assigned_to = self._parse_optional_reference_value(device_raw, 'assigned_to',
                                                                          users_table_dict, 'name')
                assigned_to = self._parse_optional_reference(device_raw, 'assigned_to', users_table_dict) or {}
                if assigned_to:
                    device.email = assigned_to.get('email')
                    device.assigned_to_country = assigned_to.get('country')
                    device.assigned_to_division = assigned_to.get('u_division')
                    try:
                        assigned_to_business_unit = (
                            # departments[assigned_to.u_business_unit].name
                            self._parse_optional_reference_value(assigned_to, 'u_business_unit',
                                                                 snow_department_table_dict, 'name') or
                            # companies[assigned_to.u_business_unit].name
                            self._parse_optional_reference_value(assigned_to, 'u_business_unit',
                                                                 companies_table_dict, 'name') or
                            # assigned_to.u_business_unit
                            assigned_to.get('u_business_unit'))
                        if isinstance(assigned_to_business_unit, str):
                            device.assigned_to_business_unit = assigned_to_business_unit
                    except Exception:
                        logger.exception(f'Problem with business unit')
                    try:
                        # users[username_to_user[assigned_to.manager]]
                        manager_sys_id = self._parse_optional_reference(assigned_to, 'manager', users_username_dict)
                        if manager_sys_id:
                            manager_raw = users_table_dict.get(manager_sys_id) or {}
                            device.manager_email = manager_raw.get('email')
                    except Exception:
                        logger.exception(f'Problem getting manager {device_raw}')
                    try:
                        device.assigned_to_location = self._parse_optional_reference_value(
                            assigned_to, 'location', snow_location_table_dict, 'name')
                    except Exception:
                        logger.exception(f'Problem getting assing to location in {device_raw}')
            except Exception:
                logger.exception(f'Problem adding assigned_to to {device_raw}')
            try:
                device.u_business_unit = (
                    self._parse_optional_reference_value(device_raw, 'u_business_unit',
                                                         snow_department_table_dict, 'name') or
                    self._parse_optional_reference_value(device_raw, 'u_business_unit',
                                                         companies_table_dict, 'name'))
            except Exception:
                logger.exception(f'Problem with device_raw u_business_unit')
            try:
                # https://localhost/devices/09dcfcde1f42fc78203276403beda5a2
                device.device_managed_by = (self._parse_optional_reference_value(device_raw, 'managed_by',
                                                                                 users_table_dict, 'name'))
            except Exception:
                logger.exception(f'Problem with device_raw u_business_unit')
            try:
                try:
                    device.vendor = self._parse_optional_reference_value(device_raw, 'vendor',
                                                                         companies_table_dict, 'name')
                except Exception:
                    logger.exception(f'Problem getting vendor for {device_raw}')
                u_vendor_ban = device_raw.get('u_vendor_ban')
                if isinstance(u_vendor_ban, str):
                    device.u_vendor_ban = u_vendor_ban
                try:
                    device.device_manufacturer = (
                        self._parse_optional_reference_value(device_raw, 'manufacturer', companies_table_dict,
                                                             'name') or
                        self._parse_optional_reference_value(curr_model_dict, 'manufacturer', companies_table_dict,
                                                             'name') or
                        device_raw.get('u_manufacturer_name'))
                except Exception:
                    logger.exception(f'Problem getting manufacturer for {device_raw}')
                cpu_manufacturer = None
                try:
                    cpu_manufacturer = self._parse_optional_reference_value(device_raw, 'cpu_manufacturer',
                                                                            companies_table_dict, 'name')
                except Exception:
                    logger.exception(f'Problem getting manufacturer for {device_raw}')
                ghz = device_raw.get('cpu_speed')
                if ghz:
                    ghz = float(ghz) / 1024.0
                else:
                    ghz = None
                device.add_cpu(name=device_raw.get('cpu_name'),
                               cores=int(device_raw.get('cpu_count'))
                               if device_raw.get('cpu_count') else None,
                               cores_thread=int(device_raw.get('cpu_core_thread'))
                               if device_raw.get('cpu_core_thread') else None,
                               ghz=ghz,
                               manufacturer=cpu_manufacturer)
            except Exception:
                logger.exception(f'Problem adding cpu stuff to {device_raw}')
            try:
                device.company = self._parse_optional_reference_value(device_raw, 'company',
                                                                      companies_table_dict, 'name')
            except Exception:
                logger.exception(f'Problem getting company for {device_raw}')
            try:
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
                device.created_at = parse_date((device_raw.get('sys_created_on')))
                device.created_by = device_raw.get('sys_created_by')
            except Exception:
                logger.exception(f'Problem addding source stuff to {device_raw}')
            try:
                if device_raw.get('disk_space'):
                    device.add_hd(total_size=float(device_raw.get('disk_space')))
            except Exception:
                logger.exception(f'Problem adding disk stuff to {device_raw}')
            try:
                device.u_supplier = self._parse_optional_reference_value(device_raw, 'u_supplier',
                                                                         supplier_table_dict, 'u_supplier')
            except Exception:
                logger.exception(f'Problem getting supplier_info {device_raw}')
            self._fill_relation(device, device_raw.get('sys_id'), consts.RELATIONS_TABLE_PARENT_KEY,
                                relations_table_dict, relations_info_dict)
            self._fill_relation(device, device_raw.get('sys_id'), consts.RELATIONS_TABLE_CHILD_KEY,
                                relations_table_dict, relations_info_dict)
            maintenance_dict = self._parse_optional_reference(device_raw, 'maintenance_schedule',
                                                              snow_maintenance_sched_dict)
            if isinstance(maintenance_dict, dict):
                self._fill_maintenance_schedule(device, maintenance_dict)
            try:
                device.u_access_authorisers = self._parse_optional_reference_value(device_raw, 'u_access_authorisers',
                                                                                   users_table_dict, 'name')
                device.u_access_control_list_extraction_method = device_raw.get(
                    'u_access_control_list_extraction_method')
                device.u_acl_contacts = self._parse_optional_reference_value(device_raw, 'u_acl_contacts',
                                                                             users_table_dict, 'name')
                device.u_acl_contacts_mailbox = device_raw.get('u_acl_contacts_mailbox')
                device.u_atm_category = device_raw.get('u_atm_category')
                device.u_atm_line_address = device_raw.get('u_atm_line_address')
                device.u_atm_security_carrier = device_raw.get('u_atm_security_carrier')
                device.u_attestation_date = parse_date(device_raw.get('u_attestation_date'))
                device.u_bted_id = device_raw.get('u_bted_id')
                device.u_bucf_contacts = self._parse_optional_reference_value(device_raw, 'u_bucf_contacts',
                                                                              users_table_dict, 'name')
                device.u_bucf_contacts_mailbox = device_raw.get('u_bucf_contacts_mailbox')
                device.u_business_owner = self._parse_optional_reference_value(device_raw, 'u_business_owner',
                                                                               users_table_dict, 'name')
                device.u_cmdb_data_mgt_journal = device_raw.get('u_cmdb_data_mgt_journal')
                device.u_cmdb_data_owner = self._parse_optional_reference_value(device_raw, 'u_cmdb_data_owner',
                                                                                users_table_dict, 'name')
                device.u_cmdb_data_owner_group = self._parse_optional_reference_value(
                    device_raw, 'u_cmdb_data_owner_group', snow_user_groups_table_dict, 'name')
                device.u_cmdb_data_owner_team = self._parse_optional_reference_value(
                    device_raw, 'u_cmdb_data_owner_team', snow_user_groups_table_dict, 'name')
                device.u_cmdb_data_steward = self._parse_optional_reference_value(device_raw, 'u_cmdb_data_steward',
                                                                                  users_table_dict, 'name')
                device.u_custodian = self._parse_optional_reference_value(device_raw, 'u_custodian',
                                                                          users_table_dict, 'name')
                device.u_custodian_group = self._parse_optional_reference_value(device_raw, 'u_custodian_group',
                                                                                snow_user_groups_table_dict, 'name')
                device.u_custodian_team = device_raw.get('u_custodian_team')
                device.u_delivery_of_access_control_list = device_raw.get('u_delivery_of_access_control_list')
                device.u_fulfilment_group = self._parse_optional_reference_value(device_raw, 'u_fulfilment_group',
                                                                                 snow_user_groups_table_dict, 'name')
                device.u_last_update_from_import = device_raw.get('u_last_update_from_import')
                device.u_oim_division = device_raw.get('u_oim_division')
                device.u_organisation = device_raw.get('u_organisation')
                device.u_orphan_account_contacts = self._parse_optional_reference_value(
                    device_raw, 'u_orphan_account_contacts', users_table_dict, 'name')
                device.u_orphan_account_manager = self._parse_optional_reference_value(
                    device_raw, 'u_orphan_account_manager', users_table_dict, 'name')
                device.u_permitted_childless = device_raw.get('u_permitted_childless')
                device.u_permitted_parentless = device_raw.get('u_permitted_parentless')
                device.u_primary_support_group = self._parse_optional_reference_value(
                    device_raw, 'u_primary_support_group', snow_user_groups_table_dict, 'name')
                device.u_primary_support_sme = self._parse_optional_reference_value(device_raw, 'u_primary_support_sme',
                                                                                    users_table_dict, 'name')
                device.u_primary_support_team = device_raw.get('u_primary_support_team')
                device.u_reason_for_childless = device_raw.get('u_reason_for_childless')
                device.u_reason_for_parentless = device_raw.get('u_reason_for_parentless')
                device.u_recertification_approach = device_raw.get('u_recertification_approach')
                device.u_recertification_contacts = self._parse_optional_reference_value(
                    device_raw, 'u_recertification_contacts', users_table_dict, 'name')
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
                device.u_security_administrators = self._parse_optional_reference_value(device_raw,
                                                                                        'u_security_administrators',
                                                                                        users_table_dict, 'name')
                device.u_si_id = device_raw.get('u_si_id')
                device.u_source_name = device_raw.get('u_source_name')
                device.u_source_target_class = device_raw.get('u_source_target_class')
                device.u_sox_control = device_raw.get('u_sox_control')
                device.u_suspensions_deletions = device_raw.get('u_suspensions_deletions')
                device.u_technical_admin_contacts = self._parse_optional_reference_value(
                    device_raw, 'u_technical_admin_contacts', users_table_dict, 'name')
                device.u_tech_admin_mailbox = device_raw.get('u_tech_admin_mailbox')
                device.u_toxic_division_group = self._parse_optional_reference_value(
                    device_raw, 'u_toxic_division_group', snow_user_groups_table_dict, 'name')
                device.u_uar_contacts = self._parse_optional_reference_value(device_raw, 'u_uar_contacts',
                                                                             users_table_dict, 'name')
                device.u_uar_contacts_mailbox = device_raw.get('u_uar_contacts_mailbox')
                device.u_uav_delegates = self._parse_optional_reference_value(device_raw, 'u_uav_delegates',
                                                                              users_table_dict, 'name')
                device.u_work_notes = device_raw.get('u_work_notes')
            except Exception:
                logger.exception(f'Failed parsing cmdb_ci_computer_atm fields')
            try:
                device.phone_number = device_raw.get('phone_number')
                device.ci_comm_type = device_raw.get('type')
            except Exception:
                logger.exception(f'failed parsing cmdb_ci_comm fields')
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
                operational_status = operational_status_dict.get(device_raw.get('operational_status'))
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
            device.u_function = device_raw.get('u_function')
            device.u_ge_data_class = device_raw.get('u_ge_data_class')
            device.u_location_details = device_raw.get('u_location_details')

            management_access_address = device_raw.get('u_management_access_address')
            if management_access_address:
                device.u_management_access_address = management_access_address

            device.u_management_access_type = device_raw.get('u_management_access_type')
            device.u_network_zone = device_raw.get('u_network_zone')
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
        connection, install_status_dict, operational_status_dict = client_data
        with connection:
            for device_raw in connection.get_device_list(
                    fetch_users_info_for_devices=self.__fetch_users_info_for_devices,
                    fetch_ci_relations=self.__fetch_ci_relations, parallel_requests=self.__parallel_requests):
                yield device_raw, install_status_dict, operational_status_dict

    def _query_users_by_client(self, key, data):
        connection, _, _ = data
        if self.__fetch_users:
            with connection:
                yield from connection.get_user_list(parallel_requests=self.__parallel_requests)

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, raw_data):
        for user_raw in raw_data:
            try:
                # remove subtables from user_raw (otherwise query will fail due to large user_raw)
                subtables = user_raw.pop(consts.SUBTABLES_KEY, {})
                snow_department_table_dict = subtables.get(consts.DEPARTMENT_TABLE_KEY) or {}
                companies_table_dict = subtables.get(consts.COMPANY_TABLE) or {}

                user = self._new_user_adapter()
                sys_id = user_raw.get('sys_id')
                if not sys_id:
                    logger.warning(f'Bad user with no id {user_raw}')
                    continue
                user.id = sys_id
                found_whitelist = False
                mail = user_raw.get('email')
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
                    user.user_manager = (user_raw.get('manager_full') or {}).get('name')
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
                user.u_company = (self._parse_optional_reference_value(user_raw, 'u_company',
                                                                       companies_table_dict, 'name') or
                                  self._parse_optional_reference_value(user_raw, 'company',
                                                                       companies_table_dict, 'name'))
                user.u_department = (self._parse_optional_reference_value(user_raw, 'u_department',
                                                                          snow_department_table_dict, 'name') or
                                     self._parse_optional_reference_value(user_raw, 'department',
                                                                          snow_department_table_dict, 'name'))
                if user_raw.get('vip'):
                    user.u_vip = (user_raw.get('vip') == 'true')
                user.set_raw(user_raw)
                yield user
            except Exception:
                logger.warning(f'Problem getting user {user_raw}', exc_info=True)

    @staticmethod
    def _fill_relation(device, initial_sys_id, relation_key, relations_table_dict, relations_info_dict,
                       initial_depth=3) -> Optional[List[dict]]:

        # pylint: disable=no-else-return
        def _get_node_class(depth):
            if depth == 2:
                return RelativeInformationNode1
            else:
                return RelativeInformationLeaf

        def _recursive_prepare_relation(sys_id, depth):

            relations_info = relations_info_dict.get(sys_id)
            if not relations_info:
                return None

            curr_node_cls = _get_node_class(depth)
            curr_node = curr_node_cls(name=relations_info.get('name'),
                                      sys_class_name=relations_info.get('sys_class_name'))

            curr_relations = (relations_table_dict.get(sys_id) or {}).get(relation_key) or []
            # If we reached max depth or there are no relations, return only the info
            if (depth == 1) or (not curr_relations):
                return curr_node

            # parse relation
            curr_relative_objs = []
            for relative_sys_id in curr_relations:
                relative_obj = _recursive_prepare_relation(relative_sys_id, depth=depth - 1)
                if not relative_obj:
                    continue
                curr_relative_objs.append(relative_obj)

            # assign relatives
            if relation_key == consts.RELATIONS_TABLE_CHILD_KEY:
                curr_node.downstream = curr_relative_objs
            elif relation_key == consts.RELATIONS_TABLE_PARENT_KEY:
                curr_node.upstream = curr_relative_objs

            return curr_node

        try:
            # Handle initial depth differently
            # if initial sys_id has no relations of relation_key type, return None
            relative_sys_ids = (relations_table_dict.get(initial_sys_id) or {}).get(relation_key)
            if not relative_sys_ids:
                return None

            relative_objs = []
            for relative_sys_id in relative_sys_ids:
                relative_obj = _recursive_prepare_relation(relative_sys_id, depth=initial_depth - 1)
                if not relative_obj:
                    continue
                relative_objs.append(relative_obj)
            if relation_key == consts.RELATIONS_TABLE_CHILD_KEY:
                device.downstream = relative_objs
            elif relation_key == consts.RELATIONS_TABLE_PARENT_KEY:
                device.upstream = relative_objs
        except Exception:
            logger.exception(f'Failed parsing relation {relation_key}')

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
        for table_devices_data, install_status_dict, operational_status_dict in devices_raw_data:
            users_table_dict = table_devices_data.get(consts.USERS_TABLE_KEY)
            users_username_dict = table_devices_data.get(consts.USERS_USERNAME_KEY)
            snow_department_table_dict = table_devices_data.get(consts.DEPARTMENT_TABLE_KEY)
            snow_location_table_dict = table_devices_data.get(consts.LOCATION_TABLE_KEY)
            snow_user_groups_table_dict = table_devices_data.get(consts.USER_GROUPS_TABLE_KEY)
            snow_nics_table_dict = table_devices_data.get(consts.NIC_TABLE_KEY)
            snow_alm_asset_table_dict = table_devices_data.get(consts.ALM_ASSET_TABLE)
            companies_table_dict = table_devices_data.get(consts.COMPANY_TABLE)
            ips_table_dict = table_devices_data.get(consts.IPS_TABLE)
            ci_ips_table_dict = table_devices_data.get(consts.CI_IPS_TABLE)
            supplier_table_dict = table_devices_data.get(consts.U_SUPPLIER_TABLE)
            relations_table_dict = table_devices_data.get(consts.RELATIONS_TABLE)
            relations_info_dict = table_devices_data.get(consts.RELATIONS_DETAILS_TABLE_KEY)
            maintenance_sched_dict = table_devices_data.get(consts.MAINTENANCE_SCHED_TABLE)
            software_product_dict = table_devices_data.get(consts.SOFTWARE_PRODUCT_TABLE)
            model_dict = table_devices_data.get(consts.MODEL_TABLE)
            snow_logicalci_dict = table_devices_data.get(consts.LOGICALCI_TABLE)

            for device_raw in table_devices_data[consts.DEVICES_KEY]:
                device = self.create_snow_device(device_raw=device_raw,
                                                 snow_department_table_dict=snow_department_table_dict,
                                                 snow_location_table_dict=snow_location_table_dict,
                                                 snow_alm_asset_table_dict=snow_alm_asset_table_dict,
                                                 snow_nics_table_dict=snow_nics_table_dict,
                                                 users_table_dict=users_table_dict,
                                                 users_username_dict=users_username_dict,
                                                 companies_table_dict=companies_table_dict,
                                                 ci_ips_table_dict=ci_ips_table_dict,
                                                 snow_user_groups_table_dict=snow_user_groups_table_dict,
                                                 ips_table_dict=ips_table_dict,
                                                 fetch_ips=self.__fetch_ips,
                                                 table_type=table_devices_data[consts.DEVICE_TYPE_NAME_KEY],
                                                 install_status_dict=install_status_dict,
                                                 supplier_table_dict=supplier_table_dict,
                                                 relations_table_dict=relations_table_dict,
                                                 relations_info_dict=relations_info_dict,
                                                 snow_maintenance_sched_dict=maintenance_sched_dict,
                                                 snow_software_product_table_dict=software_product_dict,
                                                 snow_model_dict=model_dict,
                                                 snow_logicalci_dict=snow_logicalci_dict,
                                                 operational_status_dict=operational_status_dict)
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

        # This must be set in method override
        self.__parallel_requests = config.get('parallel_requests') or consts.DEFAULT_ASYNC_CHUNK_SIZE
