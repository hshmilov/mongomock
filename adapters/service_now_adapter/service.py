import datetime
import logging
import re
import chardet
from typing import List, Optional

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.utils.datetime import parse_date
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.exception import RESTException
from axonius.clients.service_now.connection import ServiceNowConnection
from axonius.clients.service_now.consts import *
from axonius.devices.device_adapter import DeviceAdapter
from axonius.utils.parsing import make_dict_from_csv
from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from axonius.types.correlation import CorrelationResult, CorrelationReason
from axonius.plugin_base import add_rule, return_error, EntityType
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.mixins.configurable import Configurable
logger = logging.getLogger(f'axonius.{__name__}')


class CiIpData(SmartJsonClass):
    u_authorative_dns_name = Field(str, 'Authorative DNS Name')
    u_ip_version = Field(str, 'IP Version')
    u_ip_address = Field(str, 'IP Address')
    u_lease_contract = Field(str, 'Lease Contract')
    u_netmask = Field(str, 'Netmask')
    u_network_address = Field(str, 'Network Address')
    u_subnet = Field(str, 'Subnet')
    u_zone = Field(str, 'Zone')
    u_ip_address_property = Field(str, 'IP Address Property')
    u_ip_network_class = Field(str, 'IP Network Class')
    u_last_discovered = Field(datetime.datetime, 'Last Discovered')
    u_install_status = Field(str, 'Install Status')


class MaintenanceSchedule(SmartJsonClass):
    name = Field(str, 'Name')
    ms_type = Field(str, 'Type')
    description = Field(str, 'Description')
    document = Field(str, 'Document')
    document_key = Field(str, 'Document Key')


class RelativeInformationLeaf(SmartJsonClass):
    name = Field(str, 'Name')
    sys_class_name = Field(str, 'Class Name')


class RelativeInformationNode1(RelativeInformationLeaf):
    upstream = ListField(RelativeInformationLeaf, 'Upstream')
    downstream = ListField(RelativeInformationLeaf, 'Downstream')


class ServiceNowAdapter(AdapterBase, Configurable):
    class MyUserAdapter(UserAdapter):
        snow_source = Field(str, 'ServiceNow Source')
        snow_roles = Field(str, 'Roles')
        updated_on = Field(datetime.datetime, 'Updated On')
        active = Field(str, 'Active')
        u_studio = Field(str, 'Studio')
        u_sub_department = Field(str, 'Subdepartment')
        u_saved_groups = ListField(str, 'Saved Groups')
        u_saved_roles = ListField(str, 'Saved Roles')
        u_profession = Field(str, 'Profession')

    class MyDeviceAdapter(DeviceAdapter):
        table_type = Field(str, 'Table Type')
        category = Field(str, 'Category')
        u_subcategory = Field(str, 'Subcategory')
        class_name = Field(str, 'Class Name')
        discovery_source = Field(str, 'Discovery Source')
        last_discovered = Field(datetime.datetime, 'Last Discovered')
        first_discovered = Field(datetime.datetime, 'First Discovered')
        snow_location = Field(str, 'Location')
        snow_department = Field(str, 'Department')
        fqdn = Field(str, 'Fully Qualified Domain Name')
        assigned_to = Field(str, 'Assigned To')
        install_status = Field(str, 'Install Status')
        assigned_to_location = Field(str, 'Assigned To Location')
        assigned_to_country = Field(str, 'Assigned To Country')
        assigned_to_division = Field(str, 'Assigned To Business')
        assigned_to_business_unit = Field(str, 'Assigned To Business Unit')
        manager_email = Field(str, 'Manager Email')
        purchase_date = Field(datetime.datetime, 'Purchase date')
        substatus = Field(str, 'Substatus')
        u_shared = Field(str, 'Shared')
        u_loaner = Field(str, 'Loaner')
        u_virtual_system_type = Field(str, 'Virtual System Type')
        u_cloud_premises = Field(str, 'Cloud Premises')
        u_bia_confidentiality = Field(str, 'BIA Confidentiality')
        u_bia_availability = Field(str, 'BIA Availability')
        u_bia_id = Field(str, 'BIA ID')
        u_bia_integrity = Field(str, 'BIA Integrity')
        u_bia_overall = Field(str, 'BIA Overall')
        u_casper_status = Field(str, 'Casper Status')
        u_cloud_deployment_model = Field(str, 'Cloud Deployment Model')
        u_cloud_hosted = Field(str, 'Cloud Hosted')
        u_cloud_service_type = Field(str, 'Cloud Service Type')
        u_crosssite_condition = Field(str, 'Cross site Condition')
        u_heritage = Field(str, 'Heritage')
        u_altiris_status = Field(str, 'Altiris Status')
        first_deployed = Field(datetime.datetime, 'First Deployed')
        created_at = Field(datetime.datetime, 'Created At')
        created_by = Field(str, 'Created By')
        sys_updated_on = Field(str, 'Updated On')
        used_for = Field(str, 'Used For')
        tenable_asset_group = Field(str, 'Tenable Asset Group')
        environment = Field(str, 'Environment')
        cmdb_business_function = Field(str, 'Business Function')
        management_ip = Field(str, 'Management IP')
        end_of_support = Field(str, 'End Of Support')
        firmware_version = Field(str, 'Firmware Version')
        model_version_number = Field(str, 'Model Version Number')
        operational_status = Field(str, 'Operational Status')
        hardware_status = Field(str, 'Hardware Status')
        hardware_substatus = Field(str, 'Hardware Substatus')
        vendor = Field(str, 'Vendor')
        u_vendor_ban = Field(str, 'Vendor Ban')
        u_number = Field(str, 'U Number')
        support_group = Field(str, 'Support Group')
        u_director = Field(str, 'Director')
        is_virtual = Field(bool, 'Is Virtual')
        ci_ips = ListField(CiIpData, 'CI IP Data')
        u_supplier = Field(str, 'Supplier')
        u_business_segment = Field(str, 'Business Segment')
        u_consumption_type = Field(str, 'Consumption Type')
        u_function = Field(str, 'Function')
        u_ge_data_class = Field(str, 'GE Data Class')
        u_location_details = Field(str, 'Location Details')
        u_management_access_address = Field(str, 'Management Access Address')
        u_management_access_type = Field(str, 'Management Access Type')
        u_network_zone = Field(str, 'Network Zone')
        maintenance_schedule = Field(MaintenanceSchedule, 'Maintenance Schedule')
        company = Field(str, 'Company')
        model_u_classification = Field(str, 'Model Classification')
        u_alias = Field(str, 'Alias')
        use_count = Field(int, 'Use Count')
        use_units = Field(str, 'Use Units')
        bandwidth = Field(int, 'Estimated bandwidth')
        snmp_sys_location = Field(str, 'SNMP Location')
        u_audit_tools_checked = Field(str, 'Audit Tools Checked')
        u_audit_tools_pass = Field(str, 'Audit Tools Pass')
        u_backbone = Field(str, 'Backbone')
        u_bill_ref_id = Field(str, 'Bill Ref ID')
        u_circuit_id = Field(str, 'Circuit ID')
        u_config_item_id = Field(str, 'Config Item ID')
        u_ownership_ack = Field(str, 'Ownership ACK')
        u_port_speed = Field(str, 'Port Speed')
        u_previous_assigned_to = Field(str, 'Previous Assigned To')
        u_previous_owned_by = Field(str, 'Previous Owned By')
        u_process_origin = Field(str, 'Process Origin')
        u_system_origin = Field(str, 'System Origin')
        u_uninstall_date = Field(datetime.datetime, 'Uninstall Date')
        u_access_authorisers = Field(str, 'Access Authorisers')
        u_access_control_list_extraction_method = Field(str, 'ACL Extraction Method')
        u_acl_contacts = Field(str, 'ACL Contacts')
        u_acl_contacts_mailbox = Field(str, 'ACL Contacts Mailbox')
        u_atm_category = Field(str, 'ATM Category')
        u_atm_line_address = Field(str, 'ATM Line Address')
        u_atm_security_carrier = Field(str, 'ATM Security Carrier')
        u_attestation_date = Field(datetime.datetime, 'Attestation Date')
        u_bted_id = Field(str, 'BTED ID')
        u_bucf_contacts = Field(str, 'BUCF Contacts')
        u_bucf_contacts_mailbox = Field(str, 'BUCF Contacts Mailbox')
        u_business_owner = Field(str, 'Business Owner')
        u_cmdb_data_mgt_journal = Field(str, 'Management Journal')
        u_cmdb_data_owner = Field(str, 'Data Owner')
        u_cmdb_data_owner_group = Field(str, 'Data Owner Group')
        u_cmdb_data_owner_team = Field(str, 'Data Owner Team')
        u_cmdb_data_steward = Field(str, 'Data Steward')
        u_custodian = Field(str, 'Custodian')
        u_custodian_group = Field(str, 'Custodian Group')
        u_custodian_team = Field(str, 'Custodian Team')
        u_delivery_of_access_control_list = Field(str, 'Delivery of ACL')
        u_fulfilment_group = Field(str, 'Fulfilment Group')
        u_last_update_from_import = Field(str, 'Last Update From Import')
        u_oim_division = Field(str, 'OIM Division')
        u_organisation = Field(str, 'Organisation')
        u_orphan_account_contacts = Field(str, 'Orphan Account Contacts')
        u_orphan_account_manager = Field(str, 'Orphan Account Manager')
        u_permitted_childless = Field(str, 'Permitted Childless')
        u_permitted_parentless = Field(str, 'Permitted Parentless')
        u_primary_support_group = Field(str, 'Primary Support Group')
        u_primary_support_sme = Field(str, 'Primary Support SME')
        u_primary_support_team = Field(str, 'Primary Support Team')
        u_reason_for_childless = Field(str, 'Reason For Childless')
        u_reason_for_parentless = Field(str, 'Reason For Parentless')
        u_recertification_approach = Field(str, 'Recertification Approach')
        u_recertification_contacts = Field(str, 'Recertification Contacts')
        u_recertification_type = Field(str, 'Recertification Type')
        u_record_date_time = Field(str, 'Record Date Time')
        u_record_id = Field(str, 'Record ID')
        u_record_name = Field(str, 'Record Name')
        u_ref_1_label = Field(str, 'Ref 1 Label')
        u_ref_1_value = Field(str, 'Ref 1 Value')
        u_ref_2_label = Field(str, 'Ref 2 Label')
        u_ref_2_value = Field(str, 'Ref 2 Value')
        u_ref_3_label = Field(str, 'Ref 3 Label')
        u_ref_3_value = Field(str, 'Ref 3 Value')
        u_role = Field(str, 'Role')
        u_security_administrators = Field(str, 'Security Administrators')
        u_si_id = Field(str, 'SI ID')
        u_source_name = Field(str, 'Source Name')
        u_source_target_class = Field(str, 'Source Target Class')
        u_sox_control = Field(str, 'SOX Control')
        u_suspensions_deletions = Field(str, 'Suspensions Deletions')
        u_technical_admin_contacts = Field(str, 'Technical Admin Contacts')
        u_tech_admin_mailbox = Field(str, 'Tech Admin Mailbox')
        u_toxic_division_group = Field(str, 'Toxic Division Group')
        u_uar_contacts = Field(str, 'UAR Contacts')
        u_uar_contacts_mailbox = Field(str, 'UAR Contacts Mailbox')
        u_uav_delegates = Field(str, 'UAV Delegates')
        u_work_notes = Field(str, 'Work Notes')
        phone_number = Field(str, 'Phone Number')
        ci_comm_type = Field(str, 'Type')
        # you should keep these last
        upstream = ListField(RelativeInformationNode1, 'Upstream')
        downstream = ListField(RelativeInformationNode1, 'Downstream')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_optional_reference(raw_value, reference_table: dict, reference_table_field: str):
        if not raw_value:
            return None
        if not isinstance(raw_value, dict):
            return raw_value
        raw_value = reference_table.get(raw_value.get('value'))
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
                           snow_model_dict=None):
        got_nic = False
        got_serial = False
        if not install_status_dict:
            install_status_dict = INSTALL_STATUS_DICT
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
            device.u_heritage = U_HERITAGE_DICT.get(str(device_raw.get('u_heritage'))) or device_raw.get('u_heritage')
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
                    elif re.search(RE_SQUARED_BRACKET_WRAPPED, ip_addresses):
                        # Example: [1.1.1.1] or [1.1.1.1][255.255.255.192]
                        # Note: all of the use cases ive seen had only one ip (and at most an additional subnet),
                        #       This implementation considers both as IPs in case this will actually be the case,
                        #       at most the subnet will be ignored as invalid ip
                        ip_addresses = re.findall(RE_SQUARED_BRACKET_WRAPPED, ip_addresses)
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
                snow_support_group_value = snow_user_groups_table_dict.get(
                    (device_raw.get('support_group') or {}).get('value'))
                if snow_support_group_value:
                    device.support_group = snow_support_group_value.get('name')
                    device.u_director = self._get_optional_reference(snow_support_group_value.get('u_director'),
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
            u_operating_system = device_raw.get('u_operating_system')
            if isinstance(u_operating_system, dict):
                software_product = snow_software_product_table_dict.get(u_operating_system.get('value')) or {}
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
            curr_model_dict = snow_model_dict.get((device_raw.get('model_id') or {}).get('value')) or {}
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
                    model_u_classification = (MODEL_U_CLASSIFICATION_DICT.get(model_u_classification)
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
                model_number = device_raw.get('model_number')
                if isinstance(model_number, dict):
                    device_model = model_number.get('value')
                elif curr_model_dict:
                    device_model = curr_model_dict.get('display_name')
                device.device_model = device_model
            except Exception:
                logger.warning(f'Problem getting model at {device_raw}', exc_info=True)
            try:
                device_serial = device_raw.get('serial_number')
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
                host_name = device_raw.get('host_name') or device_raw.get('fqdn') or device_raw.get('u_fqdn')
                if host_name and name and name.lower() in host_name.lower():
                    device.hostname = host_name.split('.')[0].strip()
                else:
                    alias = device_raw.get('u_alias')
                    if alias and any(bad_alias in alias.lower().strip() for bad_alias in BAD_ALIAS_NAME):
                        alias = None
                    device.u_alias = alias
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
                snow_department = snow_department_table_dict.get(
                    (device_raw.get('department') or {}).get('value'))
                if snow_department:
                    device.snow_department = snow_department.get('name')
            except Exception:
                logger.warning(f'Problem adding assigned_to to {device_raw}', exc_info=True)
            try:
                snow_asset = snow_alm_asset_table_dict.get((device_raw.get('asset') or {}).get('value'))
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
                        snow_location = snow_location_table_dict.get(
                            (snow_asset.get('location') or {}).get('value'))
                        if snow_location:
                            device.snow_location = snow_location.get('name')
                    except Exception:
                        logger.warning(f'Problem adding assigned_to to {device_raw}', exc_info=True)
                    try:
                        business_segment_id = (device_raw.get('u_business_segment') or {}).get('value')
                        business_segment = snow_department_table_dict.get(business_segment_id)
                        if isinstance(business_segment, dict):
                            device.u_business_segment = business_segment.get('name')
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
                    if self.__install_status_exclude_list and device_raw.get('install_status') and str(device_raw.get('install_status')) in self.__install_status_exclude_list:
                        return None
                except Exception:
                    logger.warning(f'Problem with install status exclude list')
            except Exception:
                logger.warning(f'Problem at asset table information {device_raw}', exc_info=True)

            owned_by = users_table_dict.get((device_raw.get('owned_by') or {}).get('value')) or {}
            if owned_by:
                device.owner = owned_by.get('name')
                if owned_by.get('email'):
                    device.email = owned_by.get('email')

            try:
                assigned_to = users_table_dict.get((device_raw.get('assigned_to') or {}).get('value'))
                if assigned_to:
                    device.assigned_to = assigned_to.get('name')
                    device.email = assigned_to.get('email')
                    device.assigned_to_country = assigned_to.get('country')
                    device.assigned_to_division = assigned_to.get('u_division')
                    try:
                        assigned_to_business_unit = assigned_to.get('u_business_unit')
                        if isinstance(assigned_to_business_unit, str):
                            device.assigned_to_business_unit = assigned_to_business_unit
                        elif isinstance(assigned_to_business_unit, dict):
                            assigned_to_business_unit_value = assigned_to_business_unit.get('value')
                            if assigned_to_business_unit_value:
                                # Not sure whether its from company table or department table
                                assgined_to_bus_name = None
                                assgined_to_bus_obj = snow_department_table_dict.get(assigned_to_business_unit_value)
                                if assgined_to_bus_obj:
                                    assgined_to_bus_name = assgined_to_bus_obj.get('name')
                                else:
                                    assgined_to_bus_obj = companies_table_dict.get(assigned_to_business_unit_value)
                                    if assgined_to_bus_obj:
                                        assgined_to_bus_name = assgined_to_bus_obj.get('name')
                                device.assigned_to_business_unit = assgined_to_bus_name
                    except Exception:
                        logger.exception(f'Problem with business unit')
                    try:
                        manager_value = (assigned_to.get('manager') or {}).get('value')
                        manager_raw = users_table_dict.get(users_username_dict.get(manager_value)) or {}
                        device.manager_email = manager_raw.get('email')
                    except Exception:
                        logger.exception(f'Problem getting manager {device_raw}')
                    try:
                        assigned_to_location_value = (assigned_to.get('location') or {}).get('value')
                        device.assigned_to_location = (snow_location_table_dict.get(
                            assigned_to_location_value) or {}).get('name')
                    except Exception:
                        logger.exception(f'Problem getting assing to location in {device_raw}')
            except Exception:
                logger.exception(f'Problem adding assigned_to to {device_raw}')

            try:
                try:
                    vendor_link = (device_raw.get('vendor') or {}).get('value')
                    if vendor_link and companies_table_dict.get(vendor_link):
                        device.vendor = companies_table_dict.get(vendor_link).get('name')
                except Exception:
                    logger.exception(f'Problem getting vendor for {device_raw}')
                u_vendor_ban = device_raw.get('u_vendor_ban')
                if isinstance(u_vendor_ban, str):
                    device.u_vendor_ban = u_vendor_ban
                try:
                    manufacturer_link = ((device_raw.get('manufacturer') or {}).get('value') or
                                         (curr_model_dict.get('manufacturer') or {}).get('value'))
                    if manufacturer_link and companies_table_dict.get(manufacturer_link):
                        device.device_manufacturer = companies_table_dict.get(manufacturer_link).get('name')
                    else:
                        device.device_manufacturer = device_raw.get('u_manufacturer_name')
                except Exception:
                    logger.exception(f'Problem getting manufacturer for {device_raw}')
                cpu_manufacturer = None
                try:
                    cpu_manufacturer_link = (device_raw.get('cpu_manufacturer') or {}).get('value')
                    if cpu_manufacturer_link and companies_table_dict.get(cpu_manufacturer_link):
                        cpu_manufacturer = companies_table_dict.get(cpu_manufacturer_link).get('name')
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
                company_link = (device_raw.get('company') or {}).get('value')
                if company_link and companies_table_dict.get(company_link):
                    device.company = companies_table_dict.get(company_link).get('name')
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
                supplier_value = (device_raw.get('u_supplier') or {}).get('value')
                if supplier_value:
                    device.u_supplier = (supplier_table_dict.get(supplier_value) or {}).get('u_supplier')
            except Exception:
                logger.exception(f'Problem getting supplier_info {device_raw}')
            self._fill_relation(device, device_raw.get('sys_id'), RELATIONS_TABLE_PARENT_KEY,
                                relations_table_dict, relations_info_dict)
            self._fill_relation(device, device_raw.get('sys_id'), RELATIONS_TABLE_CHILD_KEY,
                                relations_table_dict, relations_info_dict)
            maintenance_dict = snow_maintenance_sched_dict.get(
                (device_raw.get('maintenance_schedule') or {}).get('value'))
            if maintenance_dict:
                self._fill_maintenance_schedule(device, maintenance_dict)
            try:
                device.u_access_authorisers = self._get_optional_reference(device_raw.get('u_access_authorisers'),
                                                                           users_table_dict, 'name')
                device.u_access_control_list_extraction_method = device_raw.get(
                    'u_access_control_list_extraction_method')
                device.u_acl_contacts = self._get_optional_reference(device_raw.get('u_acl_contacts'),
                                                                     users_table_dict, 'name')
                device.u_acl_contacts_mailbox = device_raw.get('u_acl_contacts_mailbox')
                device.u_atm_category = device_raw.get('u_atm_category')
                device.u_atm_line_address = device_raw.get('u_atm_line_address')
                device.u_atm_security_carrier = device_raw.get('u_atm_security_carrier')
                device.u_attestation_date = parse_date(device_raw.get('u_attestation_date'))
                device.u_bted_id = device_raw.get('u_bted_id')
                device.u_bucf_contacts = self._get_optional_reference(device_raw.get('u_bucf_contacts'),
                                                                      users_table_dict, 'name')
                device.u_bucf_contacts_mailbox = device_raw.get('u_bucf_contacts_mailbox')
                device.u_business_owner = self._get_optional_reference(device_raw.get('u_business_owner'),
                                                                       users_table_dict, 'name')
                device.u_cmdb_data_mgt_journal = device_raw.get('u_cmdb_data_mgt_journal')
                device.u_cmdb_data_owner = self._get_optional_reference(device_raw.get('u_cmdb_data_owner'),
                                                                        users_table_dict, 'name')
                device.u_cmdb_data_owner_group = self._get_optional_reference(device_raw.get('u_cmdb_data_owner_group'),
                                                                              snow_user_groups_table_dict, 'name')
                device.u_cmdb_data_owner_team = self._get_optional_reference(device_raw.get('u_cmdb_data_owner_team'),
                                                                             snow_user_groups_table_dict, 'name')
                device.u_cmdb_data_steward = self._get_optional_reference(device_raw.get('u_cmdb_data_steward'),
                                                                          users_table_dict, 'name')
                device.u_custodian = self._get_optional_reference(device_raw.get('u_custodian'),
                                                                  users_table_dict, 'name')
                device.u_custodian_group = self._get_optional_reference(device_raw.get('u_custodian_group'),
                                                                        snow_user_groups_table_dict, 'name')
                device.u_custodian_team = device_raw.get('u_custodian_team')
                device.u_delivery_of_access_control_list = device_raw.get('u_delivery_of_access_control_list')
                device.u_fulfilment_group = self._get_optional_reference(device_raw.get('u_fulfilment_group'),
                                                                         snow_user_groups_table_dict, 'name')
                device.u_last_update_from_import = device_raw.get('u_last_update_from_import')
                device.u_oim_division = device_raw.get('u_oim_division')
                device.u_organisation = device_raw.get('u_organisation')
                device.u_orphan_account_contacts = self._get_optional_reference(device_raw.get('u_orphan_account_contacts'),
                                                                                users_table_dict, 'name')
                device.u_orphan_account_manager = self._get_optional_reference(device_raw.get('u_orphan_account_manager'),
                                                                               users_table_dict, 'name')
                device.u_permitted_childless = device_raw.get('u_permitted_childless')
                device.u_permitted_parentless = device_raw.get('u_permitted_parentless')
                device.u_primary_support_group = self._get_optional_reference(device_raw.get('u_primary_support_group'),
                                                                              snow_user_groups_table_dict, 'name')
                device.u_primary_support_sme = self._get_optional_reference(device_raw.get('u_primary_support_sme'),
                                                                            users_table_dict, 'name')
                device.u_primary_support_team = device_raw.get('u_primary_support_team')
                device.u_reason_for_childless = device_raw.get('u_reason_for_childless')
                device.u_reason_for_parentless = device_raw.get('u_reason_for_parentless')
                device.u_recertification_approach = device_raw.get('u_recertification_approach')
                device.u_recertification_contacts = self._get_optional_reference(device_raw.get('u_recertification_contacts'),
                                                                                 users_table_dict, 'name')
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
                device.u_security_administrators = self._get_optional_reference(device_raw.get('u_security_administrators'),
                                                                                users_table_dict, 'name')
                device.u_si_id = device_raw.get('u_si_id')
                device.u_source_name = device_raw.get('u_source_name')
                device.u_source_target_class = device_raw.get('u_source_target_class')
                device.u_sox_control = device_raw.get('u_sox_control')
                device.u_suspensions_deletions = device_raw.get('u_suspensions_deletions')
                device.u_technical_admin_contacts = self._get_optional_reference(device_raw.get('u_technical_admin_contacts'),
                                                                                 users_table_dict, 'name')
                device.u_tech_admin_mailbox = device_raw.get('u_tech_admin_mailbox')
                device.u_toxic_division_group = self._get_optional_reference(device_raw.get('u_toxic_division_group'),
                                                                             snow_user_groups_table_dict, 'name')
                device.u_uar_contacts = self._get_optional_reference(device_raw.get('u_uar_contacts'),
                                                                     users_table_dict, 'name')
                device.u_uar_contacts_mailbox = device_raw.get('u_uar_contacts_mailbox')
                device.u_uav_delegates = self._get_optional_reference(device_raw.get('u_uav_delegates'),
                                                                      users_table_dict, 'name')
                device.u_work_notes = device_raw.get('u_work_notes')
            except Exception:
                logger.exception(f'Failed parsing cmdb_ci_computer_atm fields')
            try:
                device.phone_number = device_raw.get('phone_number')
                device.ci_comm_type = device_raw.get('type')
            except Exception:
                logger.exception(f'failed parsing cmdb_ci_comm fields')
            device.domain = device_raw.get('dns_domain')
            device.used_for = device_raw.get('used_for')
            device.tenable_asset_group = device_raw.get('u_tenable_asset_group')
            u_environment = device_raw.get('u_environment')
            device.environment = U_ENVIRONMENT_DICT.get(str(u_environment)) or u_environment
            device.cmdb_business_function = device_raw.get('u_cmdb_business_function')
            device.management_ip = device_raw.get('u_management_ip')
            device.end_of_support = device_raw.get('u_end_of_support')
            device.firmware_version = device_raw.get('u_firmware_version')
            device.model_version_number = device_raw.get('u_model_version_number')
            if self.__fetch_operational_status:
                device.operational_status = install_status_dict.get(device_raw.get('operational_status'))
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

    def _get_client_id(self, client_config):
        return client_config['domain']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        https_proxy = client_config.get('https_proxy')
        if https_proxy and https_proxy.startswith('http://'):
            https_proxy = 'https://' + https_proxy[len('http://'):]
        connection = ServiceNowConnection(
            domain=client_config['domain'], verify_ssl=client_config['verify_ssl'],
            username=client_config['username'],
            password=client_config['password'], https_proxy=https_proxy)
        with connection:
            pass  # check that the connection credentials are valid
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config), self._get_install_status_dict(client_config)
        except RESTException as e:
            message = 'Error connecting to client with domain {0}, reason: {1}'.format(
                client_config['domain'], str(e))
            logger.warning(message, exc_info=True)
            raise ClientConnectionException(message)

    def _get_install_status_dict(self, client_config):
        install_status_dict = dict()
        try:
            if client_config.get('install_status_file'):
                csv_data_bytes = self._grab_file_contents(client_config['install_status_file'])
                encoding = chardet.detect(csv_data_bytes)['encoding']  # detect decoding automatically
                encoding = encoding or 'utf-8'
                csv_data = csv_data_bytes.decode(encoding)
                csv_data = make_dict_from_csv(csv_data)
                if 'Value' in csv_data.fieldnames and 'Label' in csv_data.fieldnames:
                    for csv_line in csv_data:
                        if csv_line.get('Value') and csv_line.get('Label'):
                            install_status_dict[str(csv_line['Value'])] = csv_line['Label']

        except Exception:
            logger.exception(f'Problem parsing install status dict')
        return install_status_dict

    def _query_devices_by_client(self, client_name, client_data):
        """
        Get all devices from a specific ServiceNow domain

        :param str client_name: The name of the client
        :param obj client_data: The data that represent a ServiceNow connection

        :return: A json with all the attributes returned from the ServiceNow Server
        """
        connection, install_status_dict = client_data
        with connection:
            for device_raw in connection.get_device_list(
                    fetch_users_info_for_devices=self.__fetch_users_info_for_devices,
                    fetch_ci_relations=self.__fetch_ci_relations):
                yield device_raw, install_status_dict

    def _query_users_by_client(self, key, data):
        connection, _ = data
        if self.__fetch_users:
            with connection:
                yield from connection.get_user_list()

    def _clients_schema(self):
        """
        The schema ServiceNowAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'ServiceNow Domain',
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
                    'name': 'install_status_file',
                    'title': 'Install Status ENUM CSV File',
                    'type': 'file'
                },
            ],
            'required': [
                'domain',
                'username',
                'password',
                'verify_ssl'
            ],
            'type': 'array'
        }

    @add_rule('update_computer', methods=['POST'])
    def update_service_now_computer(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        service_now_connection = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status, device_raw = conn.update_service_now_computer(service_now_connection)
                    success = success or result_status
                    if success is True:
                        device = self.create_snow_device(device_raw=device_raw,
                                                         fetch_ips=self.__fetch_ips)
                        if device:
                            device_dict = device.to_dict()
                            self._save_data_from_plugin(
                                client_id,
                                {'raw': [], 'parsed': [device_dict]},
                                EntityType.Devices, False)
                            self._save_field_names_to_db(EntityType.Devices)
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    @add_rule('create_incident', methods=['POST'])
    def create_service_now_incident(self):
        if self.get_method() != 'POST':
            return return_error('Medhod not supported', 405)
        service_now_dict = self.get_request_data_as_object()
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    success = success or conn.create_service_now_incident(service_now_dict)
                    if success is True:
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    @add_rule('create_computer', methods=['POST'])
    def create_service_now_computer(self):
        if self.get_method() != 'POST':
            return return_error('Method not supported', 405)
        request_json = self.get_request_data_as_object()
        service_now_dict = request_json.get('snow')
        success = False
        for client_id in self._clients:
            try:
                conn = self.get_connection(self._get_client_config_by_client_id(client_id))
                with conn:
                    result_status, device_raw = conn.create_service_now_computer(service_now_dict)
                    success = success or result_status
                    if success is True:
                        device = self.create_snow_device(device_raw=device_raw,
                                                         fetch_ips=self.__fetch_ips)
                        if device:
                            device_id = device.id
                            device_dict = device.to_dict()
                            self._save_data_from_plugin(
                                client_id,
                                {'raw': [], 'parsed': [device_dict]},
                                EntityType.Devices, False)
                            self._save_field_names_to_db(EntityType.Devices)
                            to_correlate = request_json.get('to_ccorrelate')
                            if isinstance(to_correlate, dict):
                                to_correlate_plugin_unique_name = to_correlate.get('to_correlate_plugin_unique_name')
                                to_correlate_device_id = to_correlate.get('device_id')
                                if to_correlate_plugin_unique_name and to_correlate_device_id:
                                    correlation_param = CorrelationResult(associated_adapters=[(to_correlate_plugin_unique_name,
                                                                                                to_correlate_device_id),
                                                                                               (self.plugin_unique_name, device_id)],
                                                                          data={'reason': 'ServiceNow Device Creation'},
                                                                          reason=CorrelationReason.ServiceNowCreation)
                                    self.link_adapters(EntityType.Devices, correlation_param)
                        return '', 200
            except Exception:
                logger.exception(f'Could not connect to {client_id}')
        return 'Failure', 400

    def _parse_users_raw_data(self, raw_data):
        for user_raw in raw_data:
            try:
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
                user.set_raw(user_raw)
                yield user
            except Exception:
                logger.warning(f'Problem getting user {user_raw}', exc_info=True)

    @staticmethod
    def _fill_relation(device, initial_sys_id, relation_key, relations_table_dict, relations_info_dict, initial_depth=3) \
            -> Optional[List[dict]]:

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
            if relation_key == RELATIONS_TABLE_CHILD_KEY:
                curr_node.downstream = curr_relative_objs
            elif relation_key == RELATIONS_TABLE_PARENT_KEY:
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
            if relation_key == RELATIONS_TABLE_CHILD_KEY:
                device.downstream = relative_objs
            elif relation_key == RELATIONS_TABLE_PARENT_KEY:
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
        for table_devices_data, install_status_dict in devices_raw_data:
            users_table_dict = table_devices_data.get(USERS_TABLE_KEY)
            users_username_dict = table_devices_data.get(USERS_USERNAME_KEY)
            snow_department_table_dict = table_devices_data.get(DEPARTMENT_TABLE_KEY)
            snow_location_table_dict = table_devices_data.get(LOCATION_TABLE_KEY)
            snow_user_groups_table_dict = table_devices_data.get(USER_GROUPS_TABLE_KEY)
            snow_nics_table_dict = table_devices_data.get(NIC_TABLE_KEY)
            snow_alm_asset_table_dict = table_devices_data.get(ALM_ASSET_TABLE)
            companies_table_dict = table_devices_data.get(COMPANY_TABLE)
            ips_table_dict = table_devices_data.get(IPS_TABLE)
            ci_ips_table_dict = table_devices_data.get(CI_IPS_TABLE)
            supplier_table_dict = table_devices_data.get(U_SUPPLIER_TABLE)
            relations_table_dict = table_devices_data.get(RELATIONS_TABLE)
            relations_info_dict = table_devices_data.get(RELATIONS_DETAILS_TABLE_KEY)
            maintenance_sched_dict = table_devices_data.get(MAINTENANCE_SCHED_TABLE)
            software_product_dict = table_devices_data.get(SOFTWARE_PRODUCT_TABLE)
            model_dict = table_devices_data.get(MODEL_TABLE)

            for device_raw in table_devices_data[DEVICES_KEY]:
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
                                                 table_type=table_devices_data[DEVICE_TYPE_NAME_KEY],
                                                 install_status_dict=install_status_dict,
                                                 supplier_table_dict=supplier_table_dict,
                                                 relations_table_dict=relations_table_dict,
                                                 relations_info_dict=relations_info_dict,
                                                 snow_maintenance_sched_dict=maintenance_sched_dict,
                                                 snow_software_product_table_dict=software_product_dict,
                                                 snow_model_dict=model_dict)
                if device:
                    yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            "items": [
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
                }
            ],
            "required": [
                'fetch_users',
                'fetch_ips', 'use_ci_table_for_install_status',
                'exclude_disposed_devices',
                'fetch_users_info_for_devices',
                'exclude_no_strong_identifier',
                'exclude_vm_tables',
                'fetch_only_active_users',
                'fetch_only_virtual_devices',
                'fetch_operational_status',
                'fetch_ci_relations'
            ],
            "pretty_name": "ServiceNow Configuration",
            "type": "array"
        }

    @classmethod
    def _db_config_default(cls):
        return {
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

    def _on_config_update(self, config):
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

    def outside_reason_to_live(self) -> bool:
        """
        This adapter might be called from outside, let it live
        """
        return True
