import logging

from axonius.clients.mssql.connection import MSSQLConnection
from sccm_adapter import consts

logger = logging.getLogger(f'axonius.{__name__}')


def _wrap_query_with_resource_id(query, device_id, resource_name=None):
    if not resource_name:
        resource_name = 'ResourceID'
    if not device_id:
        return query
    return f'{query} WHERE {resource_name}=\'{device_id}\''


def _create_sccm_client_connection(client_config, devices_fetched_at_a_time) -> MSSQLConnection:
    connection = MSSQLConnection(
        database=client_config[consts.SCCM_DATABASE],
        server=client_config[consts.SCCM_HOST],
        port=client_config.get(consts.SCCM_PORT) or consts.DEFAULT_SCCM_PORT,
        devices_paging=devices_fetched_at_a_time,
    )
    connection.set_credentials(username=client_config[consts.USER], password=client_config[consts.PASSWORD])

    return connection


# pylint: disable=too-many-locals, too-many-nested-blocks, too-many-branches, too-many-statements
def sccm_query_devices_by_client(client_config, devices_fetched_at_a_time, device_id=None):
    client_data = _create_sccm_client_connection(client_config, devices_fetched_at_a_time)
    client_data.set_devices_paging(devices_fetched_at_a_time)
    with client_data:
        guard_compliance_dict = dict()
        try:
            if not device_id:
                for guard_data in client_data.query(consts.GUARD_COMPLIANCE_QUERY):
                    machine_id = guard_data.get('ResourceID')
                    if not machine_id:
                        continue
                    guard_compliance_dict[machine_id] = guard_data
        except Exception:
            logger.exception(f'Problem with online dict')

        online_dict = dict()
        try:
            if not device_id:
                for online_data in client_data.query(consts.ONLINE_QUERY):
                    machine_id = online_data.get('MachineID')
                    if not machine_id:
                        continue
                    online_dict[machine_id] = online_data
        except Exception:
            logger.exception(f'Problem with online dict')

        product_files_dict = dict()
        try:
            if not device_id:
                for file_data in client_data.query(consts.FILE_PRODUCT_QUERY):
                    product_id = file_data.get('ProductId')
                    if not product_id:
                        continue
                    product_files_dict[product_id] = file_data
        except Exception:
            logger.exception(f'Problem with product file dict')

        svc_dict = dict()
        try:
            for svc_data in client_data.query(_wrap_query_with_resource_id(consts.SVC_QUERY, device_id)):
                asset_id = svc_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in svc_dict:
                    svc_dict[asset_id] = []
                svc_dict[asset_id].append(svc_data)
        except Exception:
            logger.warning(f'Problem getting services', exc_info=True)

        disks_dict = dict()
        try:
            for disks_data in client_data.query(_wrap_query_with_resource_id(consts.DISKS_QUERY, device_id)):
                asset_id = disks_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in disks_dict:
                    disks_dict[asset_id] = []
                disks_dict[asset_id].append(disks_data)
        except Exception:
            logger.warning(f'Problem getting Shares', exc_info=True)

        shares_dict = dict()
        try:
            for share_data in client_data.query(_wrap_query_with_resource_id(consts.SHARES_QUERY, device_id)):
                asset_id = share_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in shares_dict:
                    shares_dict[asset_id] = []
                shares_dict[asset_id].append(share_data)
        except Exception:
            logger.warning(f'Problem getting Shares', exc_info=True)

        local_admins_dict = dict()
        local_groups_dict = dict()
        try:
            for local_admin_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.LOCAL_ADMIN_QUERY, device_id)):
                asset_id = local_admin_data.get('ResourceID')
                if not asset_id:
                    continue
                if local_admin_data.get('name0') == 'Administrators':
                    if asset_id not in local_admins_dict:
                        local_admins_dict[asset_id] = []
                    local_admins_dict[asset_id].append(local_admin_data)
                if asset_id not in local_groups_dict:
                    local_groups_dict[asset_id] = []
                local_groups_dict[asset_id].append(local_admin_data)
        except Exception:
            logger.warning(f'Problem getting local admins dict', exc_info=True)

        ram_dict = dict()
        try:
            for ram_data in client_data.query(_wrap_query_with_resource_id(consts.RAM_QUERY, device_id)):
                asset_id = ram_data.get('ResourceID')
                if not asset_id or not ram_data.get('Capacity0'):
                    continue
                ram_dict[asset_id] = ram_data.get('Capacity0')
        except Exception:
            logger.warning(f'Problem getting collections data', exc_info=True)

        collections_apps_dict = dict()
        try:
            if not device_id:
                for application_collection_data in \
                        client_data.query(consts.APPLICATION_ASSIGNMENT_QUERY):
                    collection_id = application_collection_data.get('CollectionID')
                    if not collection_id:
                        continue
                    collections_apps_dict[collection_id] = application_collection_data
        except Exception:
            logger.warning(f'Problem getting application collections data', exc_info=True)

        collections_data_dict = dict()
        try:
            if not device_id:
                for collection_data_data in \
                        client_data.query(consts.COLLECTIONS_DATA_QUERY):
                    collection_id = collection_data_data.get('CollectionID')
                    if not collection_id:
                        continue
                    collections_data_dict[collection_id] = collection_data_data
        except Exception:
            logger.warning(f'Problem getting collections data', exc_info=True)

        collections_dict = dict()
        try:
            if not device_id:
                for collection_data in client_data.query(consts.COLLECTIONS_QUERY):
                    asset_id = collection_data.get('ResourceID')
                    if not asset_id:
                        continue
                    if asset_id not in collections_dict:
                        collections_dict[asset_id] = []
                    collections_dict[asset_id].append(collection_data)
        except Exception:
            logger.warning(f'Problem getting collections', exc_info=True)

        nics_dict = dict()
        try:
            for nic_data in client_data.query(_wrap_query_with_resource_id(consts.NICS_QUERY, device_id)):
                asset_id = nic_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in nics_dict:
                    nics_dict[asset_id] = []
                nics_dict[asset_id].append(nic_data)
        except Exception:
            logger.warning(f'Problem getting nics dict', exc_info=True)

        clients_dict = dict()
        try:
            for clients_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.CLIENT_SUMMARY_QUERY, device_id)):
                asset_id = clients_data.get('ResourceID')
                if not asset_id:
                    continue
                clients_dict[asset_id] = clients_data
        except Exception:
            logger.warning(f'Problem getting clietns data', exc_info=True)

        os_dict = dict()
        try:
            for os_data in client_data.query(_wrap_query_with_resource_id(consts.OS_DATA_QUERY, device_id)):
                asset_id = os_data.get('ResourceID')
                if not asset_id:
                    continue
                os_dict[asset_id] = os_data
        except Exception:
            logger.warning(f'Problem getting os data', exc_info=True)

        computer_dict = dict()
        try:
            for computer_data in \
                    client_data.query(_wrap_query_with_resource_id(consts.COMPUTER_SYSTEM_QUERY, device_id)):
                asset_id = computer_data.get('ResourceID')
                if not asset_id:
                    continue
                computer_dict[asset_id] = computer_data
        except Exception:
            logger.warning(f'Problem getting computer data', exc_info=True)

        tpm_dict = dict()
        try:
            for tpm_data in client_data.query(_wrap_query_with_resource_id(consts.TPM_QUERY, device_id)):
                asset_id = tpm_data.get('ResourceID')
                if not asset_id:
                    continue
                tpm_dict[asset_id] = tpm_data
        except Exception:
            logger.warning(f'Problem getting tpm', exc_info=True)

        owner_dict = dict()
        try:
            query_owner = _wrap_query_with_resource_id(consts.OWNER_QUERY, device_id, 'MachineID')
            for owner_data in client_data.query(query_owner):
                asset_id = owner_data.get('MachineID')
                if not asset_id:
                    continue
                owner_dict[asset_id] = owner_data
        except Exception:
            logger.warning(f'Problem getting owner', exc_info=True)

        asset_encryption_dict = dict()
        try:
            for asset_encryption_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.ENCRYPTION_QUERY, device_id)):
                asset_id = asset_encryption_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in asset_encryption_dict:
                    asset_encryption_dict[asset_id] = []
                asset_encryption_dict[asset_id].append(asset_encryption_data)
        except Exception:
            logger.warning(f'Problem getting query asset_encryption_dict', exc_info=True)

        asset_vm_dict = dict()
        try:
            for asset_vm_data in client_data.query(_wrap_query_with_resource_id(consts.VM_QUERY, device_id)):
                asset_id = asset_vm_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in asset_vm_dict:
                    asset_vm_dict[asset_id] = []
                asset_vm_dict[asset_id].append(asset_vm_data)
        except Exception:
            logger.warning(f'Problem getting vm', exc_info=True)

        mem_dict = dict()
        try:
            for mem_data in \
                    client_data.query(_wrap_query_with_resource_id(consts.MEM_QUERY, device_id)):
                asset_id = mem_data.get('ResourceID')
                if not asset_id:
                    continue
                mem_dict[asset_id] = mem_data
        except Exception:
            logger.warning(f'Problem getting mem', exc_info=True)

        asset_chasis_dict = dict()
        try:
            for asset_chasis_data in \
                    client_data.query(_wrap_query_with_resource_id(consts.CHASIS_QUERY, device_id)):
                asset_id = asset_chasis_data.get('ResourceID')
                if not asset_id:
                    continue
                asset_chasis_dict[asset_id] = asset_chasis_data
        except Exception:
            logger.warning(f'Problem getting chasis', exc_info=True)

        asset_lenovo_dict = dict()
        try:
            for asset_lenovo_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.LENOVO_QUERY, device_id)):
                asset_id = asset_lenovo_data.get('ResourceID')
                if not asset_id:
                    continue
                asset_lenovo_dict[asset_id] = asset_lenovo_data
        except Exception:
            logger.warning(f'Problem getting lenovo', exc_info=True)

        asset_top_dict = dict()
        try:
            for asset_top_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.USERS_TOP_QUERY, device_id)):
                asset_id = asset_top_data.get('ResourceID')
                if not asset_id:
                    continue
                asset_top_dict[asset_id] = asset_top_data
        except Exception:
            logger.warning(f'Problem getting top users', exc_info=True)

        asset_malware_dict = dict()
        try:
            for asset_malware_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.MALWARE_QUERY, device_id)):
                asset_id = asset_malware_data.get('ResourceID')
                if not asset_id:
                    continue
                asset_malware_dict[asset_id] = asset_malware_data
        except Exception:
            logger.warning(f'Problem getting malware data', exc_info=True)

        asset_users_dict = dict()
        try:
            query_users = _wrap_query_with_resource_id(consts.USERS_QUERY, device_id, 'MachineResourceID')
            for asset_users_data in client_data.query(query_users):
                asset_id = asset_users_data.get('MachineResourceID')
                if not asset_id:
                    continue
                if asset_id not in asset_users_dict:
                    asset_users_dict[asset_id] = []
                asset_users_dict[asset_id].append(asset_users_data)
        except Exception:
            logger.warning(f'Problem getting query users', exc_info=True)

        new_software_dict = dict()
        try:
            for new_soft_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.NEW_SOFTWARE_QUERY, device_id)):
                asset_id = new_soft_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in new_software_dict:
                    new_software_dict[asset_id] = []
                new_software_dict[asset_id].append(new_soft_data)
        except Exception:
            logger.warning(f'Problem getting query new software', exc_info=True)

        asset_software_dict = dict()
        try:
            for asset_soft_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.QUERY_SOFTWARE, device_id)):
                asset_id = asset_soft_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in asset_software_dict:
                    asset_software_dict[asset_id] = []
                asset_software_dict[asset_id].append(asset_soft_data)
        except Exception:
            logger.warning(f'Problem getting query software', exc_info=True)

        asset_program_dict = dict()
        try:
            for asset_program_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.QUERY_PROGRAM, device_id)):
                asset_id = asset_program_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in asset_program_dict:
                    asset_program_dict[asset_id] = []
                asset_program_dict[asset_id].append(asset_program_data)
        except Exception:
            logger.warning(f'Problem getting query program', exc_info=True)

        try:
            for asset_program_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.QUERY_PROGRAM_2, device_id)):
                asset_id = asset_program_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in asset_program_dict:
                    asset_program_dict[asset_id] = []
                asset_program_dict[asset_id].append(asset_program_data)
        except Exception:
            logger.warning(f'Problem getting query program', exc_info=True)

        drivers_dict = dict()
        try:
            for drivers_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.DRIVERS_QUERY, device_id)):
                asset_id = drivers_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in drivers_dict:
                    drivers_dict[asset_id] = []
                drivers_dict[asset_id].append(drivers_data)
        except Exception:
            logger.warning(f'Problem getting query patch', exc_info=True)

        network_drivers_dict = dict()
        try:
            query_network = _wrap_query_with_resource_id(consts.NETWORK_DRIVERS_QUERY, device_id)
            for network_drivers_data in client_data.query(query_network):
                asset_id = network_drivers_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in network_drivers_dict:
                    network_drivers_dict[asset_id] = []
                network_drivers_dict[asset_id].append(network_drivers_data)
        except Exception:
            logger.warning(f'Problem getting network query patch', exc_info=True)

        asset_patch_dict = dict()
        try:
            for asset_patch_data in \
                    client_data.query(_wrap_query_with_resource_id(consts.QUERY_PATCH, device_id)):
                asset_id = asset_patch_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in asset_patch_dict:
                    asset_patch_dict[asset_id] = []
                asset_patch_dict[asset_id].append(asset_patch_data)
        except Exception:
            logger.warning(f'Problem getting query patch', exc_info=True)

        try:
            for asset_patch_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.QUERY_PATCH_2, device_id)):
                asset_id = asset_patch_data.get('ResourceID')
                if not asset_id:
                    continue
                if asset_id not in asset_patch_dict:
                    asset_patch_dict[asset_id] = []
                asset_patch_dict[asset_id].append(asset_patch_data)
        except Exception:
            logger.warning(f'Problem getting query patch', exc_info=True)

        compliance_dict = dict()
        try:
            for compliance_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.COMPLIANCE_QUERY, device_id)):
                asset_id = compliance_data.get('ResourceID')
                if not asset_id:
                    continue
                compliance_dict[asset_id] = compliance_data
        except Exception:
            logger.warning(f'Problem getting compliance', exc_info=True)
        asset_bios_dict = dict()
        try:
            for asset_bios_data \
                    in client_data.query(_wrap_query_with_resource_id(consts.BIOS_QUERY, device_id)):
                asset_id = asset_bios_data.get('ResourceID')
                if not asset_id:
                    continue
                asset_bios_dict[asset_id] = asset_bios_data
        except Exception:
            logger.warning(f'Problem getting query bios', exc_info=True)
        query_main = _wrap_query_with_resource_id(consts.SCCM_MAIN_QUERY, device_id)
        devices_raw_query = list(client_data.query(query_main))
        for device_raw_original in devices_raw_query:
            device_raw = device_raw_original.copy()
            device_raw['sccm_server'] = client_data.server
            device_raw['os_data'] = os_dict.get(device_raw.get('ResourceID'))
            device_raw['computer_data'] = computer_dict.get(device_raw.get('ResourceID'))
            device_raw['users_raw'] = asset_users_dict.get(device_raw.get('ResourceID'))
            device_raw['collections_data'] = collections_dict.get(device_raw.get('ResourceID'))
            device_raw['collections_list'] = []
            device_raw['applications_list'] = []
            try:
                collections_data = device_raw['collections_data']
                if collections_data and isinstance(collections_data, list):
                    for collection_raw in collections_data:
                        try:
                            if not isinstance(collection_raw, dict) or not collection_raw.get('CollectionID'):
                                continue
                            collection_id = collection_raw.get('CollectionID')
                            if collections_data_dict.get(collection_id) and \
                                    isinstance(collections_data_dict.get(collection_id), dict) and \
                                    collections_data_dict.get(collection_id).get('Name'):
                                col_name = collections_data_dict.get(collection_id).get('Name')
                                device_raw['collections_list'].append(col_name)
                            if collections_apps_dict.get(collection_id) and \
                                    isinstance(collections_apps_dict.get(collection_id), dict) and \
                                    collections_apps_dict.get(collection_id).get('ApplicationName'):
                                app_name = collections_apps_dict.get(collection_id).get('ApplicationName')
                                device_raw['applications_list'].append(app_name)
                        except Exception:
                            logger.exception(f'Problem with collection_raw {collection_raw}')
            except Exception:
                logger.exception(f'Problem getting collections for {device_raw}')
            device_raw['encryptions_raw'] = asset_encryption_dict.get(device_raw.get('ResourceID'))
            device_raw['ram_data'] = ram_dict.get(device_raw.get('ResourceID'))
            new_sw_data = new_software_dict.get(device_raw.get('ResourceID'))
            try:
                if isinstance(new_sw_data, list):
                    for new_asset_data in new_sw_data:
                        try:
                            product_id = new_asset_data.get('ProductId')
                            if not product_id or not product_files_dict.get(product_id):
                                continue
                            new_asset_data['file_data'] = product_files_dict[product_id]
                        except Exception:
                            logger.exception(f'Problem adding new sw asset {new_asset_data}')
            except Exception:
                logger.exception(f'Problem parsing file names')
            device_raw['new_sw_data'] = new_sw_data
            device_raw['asset_software_data'] = asset_software_dict.get(device_raw.get('ResourceID'))
            device_raw['asset_program_data'] = asset_program_dict.get(device_raw.get('ResourceID'))
            device_raw['lenovo_data'] = asset_lenovo_dict.get(device_raw.get('ResourceID'))
            device_raw['patch_data'] = asset_patch_dict.get(device_raw.get('ResourceID'))
            device_raw['malware_data'] = asset_malware_dict.get(device_raw.get('ResourceID'))
            device_raw['chasis_data'] = asset_chasis_dict.get(device_raw.get('ResourceID'))
            device_raw['mem_data'] = mem_dict.get(device_raw.get('ResourceID'))
            device_raw['client_data'] = clients_dict.get(device_raw.get('ResourceID'))
            device_raw['owner_data'] = owner_dict.get(device_raw.get('ResourceID'))
            device_raw['tpm_data'] = tpm_dict.get(device_raw.get('ResourceID'))
            device_raw['vm_data'] = asset_vm_dict.get(device_raw.get('ResourceID'))
            device_raw['nic_data'] = nics_dict.get(device_raw.get('ResourceID'))
            device_raw['group_data'] = local_groups_dict.get(device_raw.get('ResourceID'))
            device_raw['local_admin_data'] = local_admins_dict.get(device_raw.get('ResourceID'))
            device_raw['drivers_data'] = drivers_dict.get(device_raw.get('ResourceID'))
            device_raw['network_drivers_data'] = network_drivers_dict.get(device_raw.get('ResourceID'))
            device_raw['share_data'] = shares_dict.get(device_raw.get('ResourceID'))
            device_raw['disks_data'] = disks_dict.get(device_raw.get('ResourceID'))
            device_raw['svc_data'] = svc_dict.get(device_raw.get('ResourceID'))
            device_raw['online_data'] = online_dict.get(device_raw.get('ResourceID'))
            device_raw['guard_compliance_data'] = guard_compliance_dict.get(device_raw.get('ResourceID'))
            device_raw['top_data'] = asset_top_dict.get(device_raw.get('ResourceID'))
            device_raw['compliance_data'] = compliance_dict.get(device_raw.get('ResourceID'))
            device_raw['bios_data'] = asset_bios_dict.get(device_raw.get('ResourceID'))

            yield device_raw
