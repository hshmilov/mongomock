import logging

from typing import Dict, Optional

from axonius.clients.service_now import consts
from axonius.clients.service_now.consts import InjectedRawFields

logger = logging.getLogger(f'axonius.{__name__}')


def _get_optional_raw_reference(device_raw: dict, field_name: str):
    if not (isinstance(device_raw, dict) and isinstance(field_name, str)):
        return None
    raw_value = device_raw.get(field_name)
    if not raw_value:
        return None
    return raw_value


def _parse_optional_reference(device_raw: dict, field_name: str, reference_table: dict,
                              use_display_value=False):
    raw_reference = _get_optional_raw_reference(device_raw, field_name)
    if not isinstance(raw_reference, dict):
        return raw_reference

    # look for sys_id in 'value'
    value = raw_reference.get('value')
    if value:
        return reference_table.get(value)

    # no value? if permitted, try display_value
    if use_display_value:
        display_value = raw_reference.get('display_value')
        if display_value:
            return display_value

    # no display_value? look for sys_id at the end of the link
    link = raw_reference.get('link')
    if link and isinstance(link, str):
        # example link: 'https://REDACTED.service-now.com/api/now/table/alm_asset/622REDACTED4bcb8
        *_, sys_id = link.rstrip('/').rsplit('/', 1)
        if sys_id:
            return reference_table.get(sys_id)

    return None


def _parse_optional_reference_value(device_raw: dict, field_name: str,
                                    reference_table: dict, reference_table_field: str):

    # In ServiceNow DataWarehouse adapter we currently don't handle raw references.
    # But, we do support references with adjacent display value "dv_*" additional fields which exist
    #     in device_raw to replace only as an alternative for reference.get('name').
    # So, If reference value asked is name, try to locate it from the raw display value beforehand.
    # See: https://jasondove.wordpress.com/2012/06/16/a-few-random-tips-for-servicenow-reporting/
    if reference_table_field == 'name':
        raw_value = device_raw.get(f'dv_{field_name}')
        if isinstance(raw_value, str) and raw_value:
            return raw_value

    raw_value = _parse_optional_reference(device_raw, field_name, reference_table,
                                          # If 'name' reference_table_field table field was requested,
                                          #     we allow the usage of display_value
                                          use_display_value=(reference_table_field == 'name'))
    if not isinstance(raw_value, dict):
        return None
    return raw_value.get(reference_table_field)


def _inject_relations(device_raw,
                      initial_sys_id,
                      relations_table_dict: dict,
                      relations_info_dict: dict):

    def _recur_inject_relatives(curr_relations, node_raw, curr_depth):

        # Implicit recursion stop - no relatives, no recursion
        if not (curr_relations and isinstance(curr_relations, dict)):
            return

        downstream_relatives = curr_relations.get(consts.RELATIONS_TABLE_CHILD_KEY)
        if isinstance(downstream_relatives, list):
            node_raw[consts.RELATIONS_TABLE_CHILD_KEY] = [
                _recur_join_relations(sys_id, curr_depth - 1)
                for sys_id in downstream_relatives
            ]

        upstream_relatives = curr_relations.get(consts.RELATIONS_TABLE_PARENT_KEY)
        if isinstance(upstream_relatives, list):
            node_raw[consts.RELATIONS_TABLE_PARENT_KEY] = [
                _recur_join_relations(sys_id, curr_depth - 1)
                for sys_id in upstream_relatives
            ]

    def _recur_join_relations(curr_sys_id, curr_depth):
        curr_relations_info = relations_info_dict.get(curr_sys_id)
        if not isinstance(curr_relations_info, dict):
            return None

        # copy it so we dont inject relative information to the original table
        curr_relations_info = curr_relations_info.copy()

        # Explicit recursion stop - last depth only have relations info
        if curr_depth == 1:
            return curr_relations_info

        # Inject relatives
        _recur_inject_relatives(relations_table_dict.get(curr_sys_id),
                                curr_relations_info,
                                curr_depth)

        return curr_relations_info

    try:
        _recur_inject_relatives(relations_table_dict.get(initial_sys_id),
                                device_raw,
                                consts.MAX_RELATIONS_DEPTH)
    except Exception:
        logger.debug(f'Failed setting relations data', exc_info=True)

# pylint: disable=too-many-locals,too-many-branches,too-many-statements


def _inject_extra_fields(device_raw, extra_fields_definition: dict):
    # pylint: disable
    for field_enum, raw_options in extra_fields_definition.items():
        value = None
        if isinstance(raw_options, str):
            value = device_raw.get(raw_options)
        elif isinstance(raw_options, list):
            for raw_option in raw_options:
                raw_option = device_raw.get(raw_option)
                if isinstance(raw_option, dict):
                    # if we got a reference, lets try to use its display value
                    raw_option = raw_option.get('display_value') or raw_option
                if raw_option:
                    value = raw_option
                    break
        else:
            # SHOULD NEVER GET TO HERE
            logger.error('Implemetation error - inadhearance to DEVICE_EXTRA_FIELDS_BY_TARGET type')
            continue

        if value:
            device_raw[field_enum.value] = value


def inject_subtables_fields_to_device(device_subtables_data: Dict[str, dict],
                                      device_raw: dict,
                                      use_dotwalking: Optional[bool]=True):

    if not (isinstance(device_subtables_data, dict) and isinstance(device_raw, dict)):
        logger.warning(f'Invalid subtables retrieved: {device_subtables_data}')
        return

    # Most of these will be an empty dict
    users_table_dict = device_subtables_data.get(consts.USERS_TABLE_KEY) or {}
    users_username_dict = device_subtables_data.get(consts.USERS_USERNAME_KEY) or {}
    snow_nics_table_dict = device_subtables_data.get(consts.NIC_TABLE_KEY) or {}
    ips_table_dict = device_subtables_data.get(consts.IPS_TABLE) or {}
    ci_ips_table_dict = device_subtables_data.get(consts.CI_IPS_TABLE) or {}
    snow_location_table_dict = device_subtables_data.get(consts.LOCATION_TABLE_KEY) or {}
    snow_department_table_dict = device_subtables_data.get(consts.DEPARTMENT_TABLE_KEY) or {}
    snow_user_groups_table_dict = device_subtables_data.get(consts.USER_GROUPS_TABLE_KEY) or {}
    snow_alm_asset_table_dict = device_subtables_data.get(consts.ALM_ASSET_TABLE) or {}
    companies_table_dict = device_subtables_data.get(consts.COMPANY_TABLE) or {}
    business_unit_dict = device_subtables_data.get(consts.BUSINESS_UNIT_TABLE) or {}
    u_division_dict = device_subtables_data.get(consts.U_DIVISION_TABLE) or {}
    supplier_table_dict = device_subtables_data.get(consts.U_SUPPLIER_TABLE) or {}
    software_product_dict = device_subtables_data.get(consts.SOFTWARE_PRODUCT_TABLE) or {}
    model_dict = device_subtables_data.get(consts.MODEL_TABLE) or {}
    snow_logicalci_dict = device_subtables_data.get(consts.LOGICALCI_TABLE) or {}
    relations_table_dict = device_subtables_data.get(consts.RELATIONS_TABLE) or {}
    relations_info_dict = device_subtables_data.get(consts.RELATIONS_DETAILS_TABLE_KEY) or {}
    maintenance_sched_dict = device_subtables_data.get(consts.MAINTENANCE_SCHED_TABLE) or {}
    snow_compliance_exc_ids_dict = device_subtables_data.get(consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE) or {}
    snow_compliance_exc_data_dict = device_subtables_data.get(consts.COMPLIANCE_EXCEPTION_DATA_TABLE) or {}
    #snow_no_sam_software_by_ci_dict = device_subtables_data.get(consts.SOFTWARE_NO_SAM_TO_CI_TABLE) or {}
    snow_sam_software_by_ci_dict = device_subtables_data.get(consts.SOFTWARE_SAM_TO_CI_TABLE) or {}
    contract_rel_dict = device_subtables_data.get(consts.CONTRACT_TO_ASSET_TABLE) or {}
    contract_rel_data_dict = device_subtables_data.get(consts.CONTRACT_DETAILS_TABLE_KEY) or {}
    verification_table_dict = device_subtables_data.get(consts.VERIFICATION_TABLE) or {}

    if use_dotwalking:
        # inject ServiceNow dot-walked fields
        _inject_extra_fields(device_raw, extra_fields_definition=consts.DEVICE_EXTRA_FIELDS_BY_TARGET)

    try:
        snow_nics = snow_nics_table_dict.get(device_raw.get('sys_id'))
        device_raw[InjectedRawFields.snow_nics.value] = snow_nics
        if isinstance(snow_nics, list):
            device_raw[InjectedRawFields.ci_ip_data.value] = [
                ci_ips_table_dict.get(snow_nic.get('correlation_id'))
                for snow_nic in snow_nics
                if (isinstance(snow_nic, dict) and
                    snow_nic.get('correlation_id') and
                    ci_ips_table_dict.get(snow_nic.get('correlation_id')))
            ]
    except Exception:
        logger.exception(f'Failed parsing snow_nics')

    try:
        device_raw[InjectedRawFields.snow_ips.value] = ips_table_dict.get(device_raw.get('sys_id'))
    except Exception:
        logger.exception(f'Failed parsing snow_ips')

    try:
        # users[username_to_user[assigned_to.manager]]
        manager_username = device_raw.pop(InjectedRawFields.assigned_to_manager, None)
        manager_sys_id = users_username_dict.get(manager_username)
        if manager_sys_id:
            manager_raw = users_table_dict.get(manager_sys_id) or {}
            device_raw[InjectedRawFields.manager_email.value] = manager_raw.get('email')
    except Exception:
        logger.exception(f'Problem getting manager {device_raw}')

    device_raw[InjectedRawFields.maintenance_schedule.value] = \
        _parse_optional_reference(device_raw, 'maintenance_schedule', maintenance_sched_dict)

    try:
        # prepare compliance exception ids
        device_compliance_exception_ids_set = set()
        id_based_exceptions = snow_compliance_exc_ids_dict.get(device_raw.get('sys_id'))
        if isinstance(id_based_exceptions, list):
            device_compliance_exception_ids_set.update(id_based_exceptions)
        if device_raw.get('name') and isinstance(device_raw.get('name'), str):
            name_based_exceptions = snow_compliance_exc_ids_dict.get(device_raw.get('name').lower())
            if isinstance(name_based_exceptions, list):
                device_compliance_exception_ids_set.update(name_based_exceptions)

        # parse compliance exceptions
        if device_compliance_exception_ids_set:
            device_raw[InjectedRawFields.compliance_exceptions.value] = [
                snow_compliance_exc_data_dict.get(compliance_exception_id)
                for compliance_exception_id in device_compliance_exception_ids_set
            ]
    except Exception:
        logger.exception(f'Failed injecting compliance exceptions')

    try:
        # prepare software ids
        # snow_no_sam_software_by_ci_dict.get(device_raw.get('sys_id')) or
        device_installed_software = snow_sam_software_by_ci_dict.get(device_raw.get('sys_id'))
        if device_installed_software and isinstance(device_installed_software, list):
            device_raw[InjectedRawFields.snow_software.value] = device_installed_software
    except Exception:
        logger.exception(f'Failed injecting software')

    try:
        device_contract_numbers = contract_rel_dict.get(device_raw.get('sys_id'))
        device_contracts_by_number = {}
        if isinstance(device_contract_numbers, list):
            for contract_number in device_contract_numbers:
                contract_data = contract_rel_data_dict.get(contract_number)
                if isinstance(contract_data, dict):
                    device_contracts_by_number.setdefault(contract_number, contract_data)
                elif contract_data:
                    logger.debug(f'Invalid contract not a dict: {type(contract_data)}')
        elif device_contract_numbers:
            logger.debug(f'Invalid device contract numbers: {type(device_contract_numbers)}')
        if device_contracts_by_number:
            device_raw[InjectedRawFields.contracts.value] = list(device_contracts_by_number.values())

    except Exception:
        logger.exception(f'Failed injecting contract information')

    try:
        device_verification_data = verification_table_dict.get(device_raw.get('sys_id'))
        if device_verification_data:
            device_raw[InjectedRawFields.verification_status.value] = device_verification_data.get('status')
            device_raw[InjectedRawFields.verification_operational_status.value] = \
                device_verification_data.get('operational_status')
    except Exception:
        logger.exception(f'Failed injecting verification information')

    try:
        device_raw[InjectedRawFields.owner_name.value] = \
            _parse_optional_reference_value(device_raw, 'owned_by', users_table_dict, 'name')
        owned_by = _parse_optional_reference(device_raw, 'owned_by', users_table_dict) or {}
        if owned_by:
            device_raw[InjectedRawFields.owner_email.value] = owned_by.get('name')

        device_raw[InjectedRawFields.assigned_to_name.value] = \
            _parse_optional_reference_value(device_raw, 'assigned_to', users_table_dict, 'name')
        assigned_to = _parse_optional_reference(device_raw, 'assigned_to', users_table_dict) or {}
        if assigned_to and isinstance(assigned_to, dict):
            # subtables only
            try:
                device_raw[InjectedRawFields.assigned_to_u_division.value] = (
                    # u_division[assigned_to.u_division].name
                    _parse_optional_reference_value(assigned_to, 'u_division', u_division_dict, 'name') or
                    assigned_to.get('u_division'))
                device_raw[InjectedRawFields.assigned_to_business_unit.value] = (
                    # departments[assigned_to.u_business_unit].name
                    _parse_optional_reference_value(assigned_to, 'u_business_unit',
                                                    snow_department_table_dict, 'name') or
                    # companies[assigned_to.u_business_unit].name
                    _parse_optional_reference_value(assigned_to, 'u_business_unit',
                                                    companies_table_dict, 'name') or
                    # business_unit[assigned_to.u_business_unit].name
                    _parse_optional_reference_value(assigned_to, 'u_business_unit',
                                                    business_unit_dict, 'name') or
                    # assigned_to.u_business_unit
                    assigned_to.get('u_business_unit'))
            except Exception:
                logger.exception(f'Problem with assigned_to / business unit')

        try:
            device_raw.setdefault(InjectedRawFields.assigned_to_location.value,
                                  _parse_optional_reference_value(assigned_to, 'location',
                                                                  snow_location_table_dict, 'name'))
        except Exception:
            logger.exception(f'Problem getting assigned_to_location in {device_raw}')

        try:
            device_raw.setdefault(InjectedRawFields.u_division.value,
                                  assigned_to.get('u_division') or owned_by.get('u_division'))
            device_raw.setdefault(InjectedRawFields.u_level1_mgmt_org_code.value,
                                  assigned_to.get('u_level1_mgmt_org_code') or
                                  owned_by.get('u_level1_mgmt_org_code'))
            device_raw.setdefault(InjectedRawFields.u_level2_mgmt_org_code.value,
                                  assigned_to.get('u_level2_mgmt_org_code') or
                                  owned_by.get('u_level2_mgmt_org_code'))
            device_raw.setdefault(InjectedRawFields.u_level3_mgmt_org_code.value,
                                  assigned_to.get('u_level3_mgmt_org_code') or
                                  owned_by.get('u_level3_mgmt_org_code'))
            device_raw.setdefault(InjectedRawFields.u_pg_email_address.value,
                                  assigned_to.get('u_pg_email_address') or
                                  owned_by.get('u_pg_email_address'))
        except Exception:
            logger.exception(f'failed parsing u_pg fields')

    except Exception:
        logger.exception(f'failed parsing assigned_to / owned_by fields in general')

    try:
        # Parse support_group
        # Some clients have support_group through u_cmdb_ci_logicalci table
        snow_logicalci_value = \
            _parse_optional_reference(device_raw, 'u_logical_ci', snow_logicalci_dict) or {}

        device_raw.setdefault(InjectedRawFields.support_group.value,
                              _parse_optional_reference_value(device_raw, 'support_group',
                                                              snow_user_groups_table_dict, 'name') or
                              _parse_optional_reference_value(snow_logicalci_value, 'support_group',
                                                              snow_user_groups_table_dict, 'name'))
        snow_support_group_value = (_parse_optional_reference(device_raw, 'support_group',
                                                              snow_user_groups_table_dict) or
                                    _parse_optional_reference(snow_logicalci_value, 'support_group',
                                                              snow_user_groups_table_dict))
        if isinstance(snow_support_group_value, dict):
            # subtables only
            device_raw[InjectedRawFields.u_director.value] = \
                _parse_optional_reference_value(snow_support_group_value, 'u_director',
                                                users_table_dict, 'name')
            device_raw[InjectedRawFields.u_manager.value] = \
                _parse_optional_reference_value(snow_support_group_value, 'u_manager',
                                                users_table_dict, 'name')
    except Exception:
        logger.warning(f'Problem adding support group to {device_raw}', exc_info=True)

    u_operating_system = _parse_optional_reference(device_raw, 'u_operating_system', software_product_dict)
    if u_operating_system and isinstance(u_operating_system, dict):
        # subtables only
        device_raw[InjectedRawFields.os_title.value] = u_operating_system.get('title')
        device_raw[InjectedRawFields.major_version.value] = u_operating_system.get('major_version')
        device_raw[InjectedRawFields.minor_version.value] = u_operating_system.get('minor_version')
        device_raw[InjectedRawFields.build_version.value] = u_operating_system.get('build_version')

    curr_model_dict = _parse_optional_reference(device_raw, 'model_id', model_dict) or {}

    try:
        device_raw.setdefault(InjectedRawFields.model_u_classification.value,
                              _parse_optional_reference_value(device_raw, 'model_id', model_dict, 'u_classification'))

        device_raw.setdefault(InjectedRawFields.device_model.value,
                              _get_optional_raw_reference(device_raw, 'model_number') or
                              _parse_optional_reference_value(device_raw, 'model_id',
                                                              model_dict, 'name') or
                              curr_model_dict.get('display_name'))
    except Exception:
        logger.warning(f'Problem getting model at {device_raw}', exc_info=True)

    try:
        device_raw.setdefault(InjectedRawFields.snow_department.value,
                              _parse_optional_reference_value(device_raw, 'department',
                                                              snow_department_table_dict, 'name'))
    except Exception:
        logger.warning(f'Problem adding snow_department to {device_raw}', exc_info=True)
    try:
        device_raw.setdefault(InjectedRawFields.physical_location.value,
                              _parse_optional_reference_value(device_raw, 'location', snow_location_table_dict, 'name'))
    except Exception:
        logger.warning(f'Problem adding physical_location to {device_raw}', exc_info=True)

    snow_asset = _parse_optional_reference(device_raw, 'asset', snow_alm_asset_table_dict) or {}
    if snow_asset:
        # subtables only
        device_raw[InjectedRawFields.asset_install_status.value] = snow_asset.get('install_status')
        device_raw[InjectedRawFields.asset_u_loaner.value] = snow_asset.get('u_loaner')
        device_raw[InjectedRawFields.asset_u_shared.value] = snow_asset.get('u_shared')
        device_raw[InjectedRawFields.asset_first_deployed.value] = snow_asset.get('u_first_deployed')
        device_raw[InjectedRawFields.asset_altiris_status.value] = snow_asset.get('u_altiris_status')
        device_raw[InjectedRawFields.asset_casper_status.value] = snow_asset.get('u_casper_status')
        device_raw[InjectedRawFields.asset_substatus.value] = snow_asset.get('substatus')
        device_raw[InjectedRawFields.asset_purchase_date.value] = snow_asset.get('purchase_date')
        device_raw[InjectedRawFields.asset_last_inventory.value] = snow_asset.get('u_last_inventory')
        device_raw[InjectedRawFields.snow_location.value] = \
            _parse_optional_reference_value(snow_asset, 'location', snow_location_table_dict, 'name')

    device_raw.setdefault(InjectedRawFields.u_business_segment.value,
                          _parse_optional_reference_value(device_raw, 'u_business_segment',
                                                          snow_department_table_dict, 'name'))

    try:
        device_raw.setdefault(InjectedRawFields.u_business_unit.value,
                              _parse_optional_reference_value(device_raw, 'u_business_unit',
                                                              snow_department_table_dict, 'name') or
                              _parse_optional_reference_value(device_raw, 'u_business_unit',
                                                              companies_table_dict, 'name'))
    except Exception:
        logger.exception(f'Problem with device_raw u_business_unit')

    try:
        device_raw.setdefault(InjectedRawFields.device_managed_by.value,
                              _parse_optional_reference_value(device_raw, 'managed_by', users_table_dict, 'name'))
    except Exception:
        logger.exception(f'Problem with device_raw device_managed_by')

    try:
        device_raw.setdefault(InjectedRawFields.vendor.value,
                              _parse_optional_reference_value(device_raw, 'vendor', companies_table_dict, 'name'))
    except Exception:
        logger.exception(f'Problem getting vendor for {device_raw}')

    try:
        device_raw.setdefault(InjectedRawFields.device_manufacturer.value,
                              _parse_optional_reference_value(device_raw, 'manufacturer',
                                                              companies_table_dict, 'name') or
                              # subtable version of model_id.manufacturer.name
                              _parse_optional_reference_value(curr_model_dict, 'manufacturer',
                                                              companies_table_dict, 'name') or
                              device_raw.get('u_manufacturer_name'))
    except Exception:
        logger.exception(f'Problem getting manufacturer for {device_raw}')

    try:
        device_raw.setdefault(InjectedRawFields.cpu_manufacturer.value,
                              _parse_optional_reference_value(device_raw, 'cpu_manufacturer',
                                                              companies_table_dict, 'name'))
    except Exception:
        logger.exception(f'Problem getting manufacturer for {device_raw}')

    try:
        device_raw.setdefault(InjectedRawFields.company.value,
                              _parse_optional_reference_value(device_raw, 'company', companies_table_dict, 'name'))
    except Exception:
        logger.exception(f'Problem getting company for {device_raw}')

    try:
        device_raw.setdefault(InjectedRawFields.u_supplier.value,
                              _parse_optional_reference_value(device_raw, 'u_supplier',
                                                              supplier_table_dict, 'u_supplier') or
                              # display value
                              _parse_optional_reference_value(device_raw, 'u_supplier', {}, 'name'))
    except Exception:
        logger.exception(f'Problem getting supplier_info {device_raw}')

    try:
        device_raw.setdefault(InjectedRawFields.u_access_authorisers.value,
                              _parse_optional_reference_value(device_raw, 'u_access_authorisers', users_table_dict,
                                                              'name'))
        device_raw.setdefault(InjectedRawFields.u_acl_contacts.value,
                              _parse_optional_reference_value(device_raw, 'u_acl_contacts', users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_bucf_contacts.value,
                              _parse_optional_reference_value(device_raw, 'u_bucf_contacts', users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_business_owner.value,
                              _parse_optional_reference_value(device_raw, 'u_business_owner', users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_cmdb_data_owner.value,
                              _parse_optional_reference_value(device_raw, 'u_cmdb_data_owner', users_table_dict,
                                                              'name'))
        device_raw.setdefault(InjectedRawFields.u_cmdb_data_owner_group.value,
                              _parse_optional_reference_value(device_raw, 'u_cmdb_data_owner_group',
                                                              snow_user_groups_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_cmdb_data_owner_team.value,
                              _parse_optional_reference_value(device_raw, 'u_cmdb_data_owner_team',
                                                              snow_user_groups_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_cmdb_data_steward.value,
                              _parse_optional_reference_value(device_raw, 'u_cmdb_data_steward',
                                                              users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_custodian.value,
                              _parse_optional_reference_value(device_raw, 'u_custodian', users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_custodian_group.value,
                              _parse_optional_reference_value(device_raw, 'u_custodian_group',
                                                              snow_user_groups_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_fulfilment_group.value,
                              _parse_optional_reference_value(device_raw, 'u_fulfilment_group',
                                                              snow_user_groups_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_orphan_account_contacts.value,
                              _parse_optional_reference_value(device_raw, 'u_orphan_account_contacts',
                                                              users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_orphan_account_manager.value,
                              _parse_optional_reference_value(device_raw, 'u_orphan_account_manager',
                                                              users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_primary_support_group.value,
                              _parse_optional_reference_value(device_raw, 'u_primary_support_group',
                                                              snow_user_groups_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_primary_support_sme.value,
                              _parse_optional_reference_value(device_raw, 'u_primary_support_sme',
                                                              users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_recertification_contacts.value,
                              _parse_optional_reference_value(device_raw, 'u_recertification_contacts',
                                                              users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_security_administrators.value,
                              _parse_optional_reference_value(device_raw, 'u_security_administrators',
                                                              users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_technical_admin_contacts.value,
                              _parse_optional_reference_value(device_raw, 'u_technical_admin_contacts',
                                                              users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_toxic_division_group.value,
                              _parse_optional_reference_value(device_raw, 'u_toxic_division_group',
                                                              snow_user_groups_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_uar_contacts.value,
                              _parse_optional_reference_value(device_raw, 'u_uar_contacts',
                                                              users_table_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_uav_delegates.value,
                              _parse_optional_reference_value(device_raw, 'u_uav_delegates',
                                                              users_table_dict, 'name'))
    except Exception:
        logger.debug(f'Failed injecting general fields', exc_info=True)

    try:
        device_raw.setdefault(InjectedRawFields.u_it_owner_organization.value,
                              _parse_optional_reference_value(device_raw, 'u_it_owner_organization',
                                                              u_division_dict, 'name'))
        device_raw.setdefault(InjectedRawFields.u_managed_by_vendor.value,
                              _parse_optional_reference_value(device_raw, 'u_managed_by_vendor',
                                                              companies_table_dict, 'name'))
    except Exception:
        logger.debug(f'failed parsing it_owner_org / managed_by_vendor', exc_info=True)

    _inject_relations(device_raw, device_raw.get('sys_id'), relations_table_dict, relations_info_dict)


def inject_subtables_fields_to_user(subtables_dict: Dict[str, dict],
                                    user_raw: dict,
                                    use_dotwalking: Optional[bool]=True):

    if not isinstance(subtables_dict, dict):
        logger.warning(f'Invalid subtables retrieved: {subtables_dict}')
        return

    if use_dotwalking:
        _inject_extra_fields(user_raw,
                             extra_fields_definition=consts.USER_EXTRA_FIELDS_BY_TARGET)

    snow_department_table_dict = subtables_dict.get(consts.DEPARTMENT_TABLE_KEY) or {}
    companies_table_dict = subtables_dict.get(consts.COMPANY_TABLE) or {}

    user_raw.setdefault(InjectedRawFields.u_company.value,
                        _parse_optional_reference_value(user_raw, 'u_company', companies_table_dict, 'name') or
                        _parse_optional_reference_value(user_raw, 'company', companies_table_dict, 'name'))
    user_raw.setdefault(InjectedRawFields.u_department.value,
                        _parse_optional_reference_value(user_raw, 'u_department',
                                                        snow_department_table_dict, 'name') or
                        _parse_optional_reference_value(user_raw, 'department', snow_department_table_dict, 'name'))
