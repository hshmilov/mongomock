import datetime
import logging
from abc import abstractmethod, ABC

from typing import Optional, Dict, Tuple, Generator, List

from axonius.clients.service_now import consts
from axonius.consts.plugin_consts import USER_ADAPTERS_RAW_DB, AGGREGATOR_PLUGIN_NAME, PLUGIN_UNIQUE_NAME, \
    CORE_UNIQUE_NAME, PLUGIN_NAME
from axonius.modules.common import AxoniusCommon

logger = logging.getLogger(f'axonius.{__name__}')


class ServiceNowConnectionMixin(ABC):
    """
    Implements generic get_user_list and get_device_list for usage in ServiceNow Connection Classes.
    All that's needed is to override `connect` and `_iter_table_results_by_key`
    """

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def _iter_table_results_by_key(self, subtables_key_to_name: Dict[str, str],
                                   additional_params_by_table_key: Optional[dict] = None,
                                   parallel_requests: int = consts.DEFAULT_ASYNC_CHUNK_SIZE) \
            -> Generator[Tuple[str, dict], None, None]:
        pass

    @staticmethod
    def _prepare_relations_fields():
        fields = ['type.name']
        for relation in [consts.RELATIONS_TABLE_CHILD_KEY, consts.RELATIONS_TABLE_PARENT_KEY]:
            for relative_field in ['sys_id', 'sys_class_name', 'name']:
                fields.append(f'{relation}.{relative_field}')
        return ','.join(fields)

    @staticmethod
    def _prepare_relative_dict(relation_dict, relation):
        """ relation = RELATIONS_TABLE_CHILD_KEY | RELATIONS_TABLE_PARENT_KEY  """
        return {k.replace(f'{relation}.', '', 1): v
                for k, v in relation_dict.items()
                if (isinstance(k, str) and k.startswith(f'{relation}.'))}

    # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements,too-many-locals
    def _handle_table_result(self, table_result: dict, table_key: str, result_tables_by_key: dict):

        curr_table = result_tables_by_key.setdefault(table_key, dict())
        if not isinstance(table_result, dict):
            logger.warning(f'Invalid table_result received for key {table_key}: {table_result}')
            return

        # General subtable cases - table = {'sys_id': general subtable dict}
        if table_key in consts.GENERIC_PARSED_SUBTABLE_KEYS:
            sys_id = table_result.get('sys_id')
            if not sys_id:
                return
            if sys_id in curr_table:
                logger.debug(f'Located sys_id duplication "{sys_id}" in sub_table_key {table_key}')
                return
            curr_table[sys_id] = table_result

        elif table_key == consts.USERS_TABLE_KEY:

            sys_id = table_result.get('sys_id')
            if not sys_id:
                return
            curr_entry = curr_table.setdefault(sys_id, dict())
            # TO DO: if curr_entry.get('sys_updated_on'):
            curr_entry.update(table_result)

            # ADDITIONALLY, for users table key, configure username subtable as well
            # Note: the check for 'name' vs the usage of 'user_name' was on the original sync impl.
            username = table_result.get('user_name')
            if not (table_result.get('name') and username):
                return
            username_subtable = result_tables_by_key.setdefault(consts.USERS_USERNAME_KEY, dict())
            if username in username_subtable:
                logger.debug(f'Located username duplication "{username}" in sub_table_key {table_key}')
                return
            username_subtable[username] = table_result.get('sys_id')

        # Device Tables - curr_table = {'sys_id': device_raw, ...}
        # These are retrived from separate requests and are updated into the same raw dict
        elif table_key in consts.TABLE_NAME_BY_DEVICE_TYPE.keys():
            sys_id = table_result.get('sys_id')
            if not (sys_id and isinstance(sys_id, str)):
                logger.debug(f'got invalid sys_id for device table {table_key}: {sys_id}')
                return
            curr_entry = curr_table.setdefault(sys_id, dict())
            # TO DO: if curr_entry.get('sys_updated_on'):
            curr_entry.update(table_result)

        # CI_IPS - curr_table = {'nic_dict.u_nic': [nic dicts...]}
        elif table_key == consts.CI_IPS_TABLE:
            if not table_result.get('asset'):
                return
            curr_table.setdefault(table_result.get('u_nic'), list()).append(table_result)

        # IPS - curr_table = {'ip_dict.u_configuration_item.value': [ips dicts...]}
        elif table_key == consts.IPS_TABLE:
            configuration_item_value = (table_result.get('u_configuration_item') or {}).get('value')
            if not configuration_item_value:
                return
            curr_table.setdefault(configuration_item_value, list()).append(table_result)

        # NIC - curr_table = {'nic_dict.cmdb_ci.value': [nic dicts...]}
        elif table_key == consts.NIC_TABLE_KEY:
            cmdb_ci_value = (table_result.get('cmdb_ci') or {}).get('value')
            if not cmdb_ci_value:
                return
            curr_table.setdefault(cmdb_ci_value, list()).append(table_result)

        # Relations - curr_table = {'sys_id': {RELATIONS_PARENT: ['sys_id', ...],
        #                                      RELATIONS_CHILD: ['sys_id', ...]}
        elif table_key == consts.RELATIONS_TABLE:
            parent_sys_id = table_result.pop(f'{consts.RELATIONS_TABLE_PARENT_KEY}.sys_id', None)
            child_sys_id = table_result.pop(f'{consts.RELATIONS_TABLE_CHILD_KEY}.sys_id', None)
            if not (parent_sys_id and child_sys_id):
                return

            # Mark: parent -child> child
            parent_relations = curr_table.setdefault(parent_sys_id, {})
            parent_relations.setdefault(consts.RELATIONS_TABLE_CHILD_KEY, set()).add(child_sys_id)

            # Mark: parent <-parent- child
            child_relations = curr_table.setdefault(child_sys_id, {})
            child_relations.setdefault(consts.RELATIONS_TABLE_PARENT_KEY, set()).add(parent_sys_id)

            # prepare relatives information - {'sys_id': {'name': name, 'sys_class_name': class_name}}
            relations_details = result_tables_by_key.setdefault(consts.RELATIONS_DETAILS_TABLE_KEY, dict())

            # save parent details
            if parent_sys_id not in relations_details:
                relations_details[parent_sys_id] = self._prepare_relative_dict(
                    table_result, consts.RELATIONS_TABLE_PARENT_KEY)

            # save child details
            if child_sys_id not in relations_details:
                relations_details[child_sys_id] = self._prepare_relative_dict(
                    table_result, consts.RELATIONS_TABLE_CHILD_KEY)

        # Compliance Exception connections - (by cmdb_ci id and by profile name)
        #   curr_table = {
        #       'control.profile.cmdb_ci.value': [policy_exception.value, ...]
        #       'control.profile.name': [policy_exception.value, ...]
        #   }
        # Note: policy_exception objects are handled in the generic initial if
        elif table_key == consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE:
            policy_exception = table_result.get('policy_exception')
            if not (isinstance(policy_exception, dict) and isinstance(policy_exception.get('value'), str)):
                logger.debug(f'Compliance exception missing policy_exception: {table_result}')
                return
            policy_id = policy_exception.get('value')

            # Note: a lot of devices aren't really attached to their respective cmdb_ci object but named the same as it.
            #       policies would be attached to a device if they are attached to (in Snow) or named the same as it.
            curr_table_keys = []
            cmdb_ci = table_result.get('control.profile.cmdb_ci')
            if isinstance(cmdb_ci, dict) and isinstance(cmdb_ci.get('value'), str) and cmdb_ci.get('value'):
                curr_table_keys.append(cmdb_ci.get('value'))

            profile_name = table_result.get('control.profile.name')
            if isinstance(profile_name, str) and profile_name:
                curr_table_keys.append(profile_name.lower())

            if not curr_table_keys:
                logger.debug(f'Compliance exception missing target asset: {table_result}')
                return

            for key in curr_table_keys:
                curr_table.setdefault(key, list()).append(policy_id)

        # Software Packages Installations -
        #   curr_table = {'installed_on.sys_id': [software_dicts, ...]}
        elif table_key in [consts.SOFTWARE_SAM_TO_CI_TABLE, consts.SOFTWARE_NO_SAM_TO_CI_TABLE]:
            installed_on = table_result.get('installed_on.sys_id')
            if not installed_on:
                logger.debug(f'Software installation missing target sys_id: {table_result}')
                return

            curr_table.setdefault(installed_on, list()).append(table_result)

        # Contract information -
        #   curr_table = {'ci_item.sys_id': ['contract.number', ...}}
        #   contract_data_table = {'contract.number': contract_dict}
        elif table_key == consts.CONTRACT_TO_ASSET_TABLE:
            ci_item_id = table_result.get('ci_item.sys_id')
            if not ci_item_id:
                logger.debug(f'Contract-CI relation missing ci_item sys_id: {table_result}')
                return

            contract_number = table_result.get('contract.number')
            if not contract_number:
                logger.debug(f'Contract-CI relation missing contract.number: {table_result}')
                return
            curr_table.setdefault(ci_item_id, list()).append(contract_number)

            # Set table_result as the contract information if needed
            contract_details_dict = result_tables_by_key.setdefault(consts.CONTRACT_DETAILS_TABLE_KEY, dict())
            contract_details_dict.setdefault(contract_number, table_result)

        # Verification Table information -
        #   curr_table = {'configuration_item.sys_id': verification_table_dict}}
        elif table_key == consts.VERIFICATION_TABLE:
            ci_item_id = table_result.get('configuration_item.sys_id')
            if not ci_item_id:
                logger.debug(f'Verification table missing ci_item sys_id: {table_result}')
                return
            curr_table.setdefault(ci_item_id, table_result)

        else:
            logger.error(f'Invalid table_key encountered {table_key}: {table_result}')
            return

    # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    def _get_subtables_by_key(self, subtables_key_to_name: dict,
                              additional_params_by_table_key: Optional[dict] = None,
                              parallel_requests: int = consts.DEFAULT_ASYNC_CHUNK_SIZE):
        tables_by_key = {}

        for table_key, table_result in self._iter_table_results_by_key(
                subtables_key_to_name, additional_params_by_table_key=additional_params_by_table_key,
                parallel_requests=parallel_requests):
            # Note: all checks for validity of table_results_chunk are performed by the generator
            self._handle_table_result(table_result, table_key, tables_by_key)

        distict_ids_by_table_key = {table_key: len(subtable_by_id)
                                    for table_key, subtable_by_id in tables_by_key.items()}
        logger.info(f'Actual distict ids count: {distict_ids_by_table_key}')

        return tables_by_key

    def get_user_subtables(self, parallel_requests=consts.DEFAULT_ASYNC_CHUNK_SIZE, **_) -> Dict[str, dict]:
        return self._get_subtables_by_key(consts.USER_SUB_TABLES, parallel_requests=parallel_requests)

    # pylint: disable=too-many-arguments
    def get_device_subtables(self,
                             fetch_users_info_for_devices=False,
                             fetch_ci_relations=False,
                             fetch_compliance_exceptions=False,
                             fetch_installed_software=False,
                             fetch_software_product_model=False,
                             fetch_cmdb_model=False,
                             fetch_business_unit_dict=False,
                             parallel_requests=consts.DEFAULT_ASYNC_CHUNK_SIZE,
                             contract_parent_numbers: Optional[str]=None,
                             use_dotwalking: bool=False,
                             use_cached_users: bool=False,
                             plugin_name: Optional[str]=None,
                             **_) -> Dict[str, dict]:
        additional_params_by_table_key = {}
        sub_tables_to_request_by_key = consts.DEVICE_SUB_TABLES_KEY_TO_NAME.copy()

        if contract_parent_numbers:
            sub_tables_to_request_by_key[consts.CONTRACT_TO_ASSET_TABLE] = consts.CONTRACT_TO_ASSET_TABLE
            additional_params_by_table_key[consts.CONTRACT_TO_ASSET_TABLE] = {
                'sysparm_query': f'contract.parent.numberIN{contract_parent_numbers}'
            }

        if fetch_installed_software:
            # Once customer asks for "No SAM software info":
            #   consts.SOFTWARE_NO_SAM_TO_CI_TABLE: consts.SOFTWARE_NO_SAM_TO_CI_TABLE
            sub_tables_to_request_by_key[consts.SOFTWARE_SAM_TO_CI_TABLE] = consts.SOFTWARE_SAM_TO_CI_TABLE

        if not use_cached_users and fetch_users_info_for_devices:
            sub_tables_to_request_by_key[consts.USERS_TABLE_KEY] = consts.USERS_TABLE

        if fetch_compliance_exceptions:
            sub_tables_to_request_by_key[consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE] = \
                consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE
            sub_tables_to_request_by_key[consts.COMPLIANCE_EXCEPTION_DATA_TABLE] = \
                consts.COMPLIANCE_EXCEPTION_DATA_TABLE

        if fetch_ci_relations:
            sub_tables_to_request_by_key[consts.RELATIONS_TABLE] = consts.RELATIONS_TABLE
            # Note to future developers - for field specification, prefer using consts.TABLE_NAME_TO_FIELDS.
            #                             this approach is only for dynamic calculated ones.
            #                             consts.TABLE_NAME_TO_FIELDS values run over values set here.
            additional_params_by_table_key[consts.RELATIONS_TABLE] = {
                'sysparm_fields': self._prepare_relations_fields()
            }

        # dotwalked tables
        if not use_dotwalking:
            if fetch_cmdb_model:
                sub_tables_to_request_by_key[consts.MODEL_TABLE] = consts.MODEL_TABLE

            if fetch_software_product_model:
                sub_tables_to_request_by_key[consts.SOFTWARE_PRODUCT_TABLE] = consts.SOFTWARE_PRODUCT_TABLE

            if fetch_business_unit_dict:
                sub_tables_to_request_by_key[consts.BUSINESS_UNIT_TABLE] = consts.BUSINESS_UNIT_TABLE

        subtables_by_key = self._get_subtables_by_key(sub_tables_to_request_by_key,
                                                      additional_params_by_table_key=additional_params_by_table_key,
                                                      parallel_requests=parallel_requests)

        # inject cached users
        if use_cached_users:
            self._inject_subtables_from_axonius_db(subtables_by_key, plugin_name)

        return subtables_by_key

    @staticmethod
    def _inject_subtables_from_axonius_db(subtables_by_key,
                                          plugin_name: Optional[str]=None):

        if not plugin_name:
            logger.error(f'No plugin_name provided to subtables_from_axonius_db: {plugin_name}')
            return

        # Note: hack for supporting service_now data from different Snow Adapters' DB
        snow_adapters = ['service_now_adapter', 'service_now_akana_adapter']
        if isinstance(plugin_name, str) and plugin_name.lower() not in snow_adapters:
            snow_adapters.append(plugin_name)

        logger.info(f'Injecting subtables from Axonius DB')
        db = AxoniusCommon().db
        all_adapter_pun = db[CORE_UNIQUE_NAME]['configs']\
            .find(filter={PLUGIN_NAME: {'$in': snow_adapters}},
                  projection={PLUGIN_UNIQUE_NAME: 1}) \
            .distinct(PLUGIN_UNIQUE_NAME)
        logger.info(f'Found {all_adapter_pun} adapter clients')
        if not all_adapter_pun:
            logger.info(f'Failed to locate all PUN for Snow adapter {plugin_name}')
            return

        # Inject Users Subtable
        users_subtable = subtables_by_key.setdefault(consts.USERS_TABLE_KEY, dict())

        user_entities = db[AGGREGATOR_PLUGIN_NAME][USER_ADAPTERS_RAW_DB].find({
            PLUGIN_UNIQUE_NAME: {'$in': all_adapter_pun}
        }, projection={
            f'raw_data': 1,
        })
        for user_entity in user_entities:
            if not (isinstance(user_entity, dict) and
                    isinstance(user_entity.get('raw_data'), dict) and user_entity.get('raw_data')):
                continue
            raw_data = user_entity.get('raw_data')
            if not raw_data.get('sys_id'):
                logger.debug(f'cached user missing sys_id')
                continue
            users_subtable.setdefault(raw_data.get('sys_id'), raw_data)
        logger.info(f'Injected {len(users_subtable.keys())} cached users')

    def _iter_user_table_chunks_by_details(self,
                                           parallel_requests: int = consts.DEFAULT_ASYNC_CHUNK_SIZE,
                                           dotwalking_per_request_limit: int = consts.DEFAULT_DOTWALKING_PER_REQUEST) \
            -> Generator[Tuple[str, str, List[dict]], None, None]:

        # prepare users dict by sys_id
        tables_by_key = {}
        for table_key, table_result in self._iter_table_results_by_key(
                {consts.USERS_TABLE_KEY: consts.USERS_TABLE},
                parallel_requests=parallel_requests):
            self._handle_table_result(table_result, table_key, tables_by_key)
        users_table_dict = tables_by_key.get(consts.USERS_TABLE_KEY) or {}

        for user in users_table_dict.values():
            user_to_yield = user.copy()
            try:
                if (user.get('manager') or {}).get('value'):
                    user_to_yield['manager_full'] = users_table_dict.get(user.get('manager').get('value'))
            except Exception:
                logger.exception(f'Problem getting manager for user {user}')

            yield user_to_yield

    def get_user_list(self,
                      parallel_requests=consts.DEFAULT_ASYNC_CHUNK_SIZE,
                      dotwalking_per_request_limit: int = consts.DEFAULT_DOTWALKING_PER_REQUEST,
                      **_):
        # Note: **_ was added to support consistent calling between get_user_list and get_device_list
        #       for parallel adapter fetching

        # Note: I kept this helper method because I dont want to override get_user_list.
        #        this method is overriden in ServiceNowConnection, for Tables *REST* API handling
        yield from self._iter_user_table_chunks_by_details(
            parallel_requests=parallel_requests,
            dotwalking_per_request_limit=dotwalking_per_request_limit)

    def _iter_device_table_chunks_by_details(self,
                                             parallel_requests: int = consts.DEFAULT_ASYNC_CHUNK_SIZE,
                                             last_seen_timedelta: Optional[datetime.timedelta] = None,
                                             dotwalking_per_request_limit: int=consts.DEFAULT_DOTWALKING_PER_REQUEST,
                                             **_) -> Generator[Tuple[str, str, List[dict]], None, None]:

        additional_params_by_table_key = {}
        if isinstance(last_seen_timedelta, datetime.timedelta):
            last_timestamp = datetime.datetime.utcnow() - last_seen_timedelta
            last_date = last_timestamp.strftime('%Y-%m-%d')
            last_time = last_timestamp.strftime('%H:%M:%S')

            # pylint: disable=line-too-long
            # https://community.servicenow.com/community?id=community_question&sys_id=ba88032adb9ee780fb115583ca9619e4&view_source=searchResult
            last_seen_query = f'sys_updated_on>javascript:gs.dateGenerate(\'{last_date}\',\'{last_time}\')'
            # pylint: enable=line-too-long

            # set the current query for all the devices
            # pylint: disable=consider-iterating-dictionary
            additional_params_by_table_key.update({table_key: {'sysparm_query': last_seen_query}
                                                   for table_key in consts.TABLE_NAME_BY_DEVICE_TYPE.keys()})

        # prepare table_name_by_key for async requests
        for device_type, table_result in self._iter_table_results_by_key(
                consts.TABLE_NAME_BY_DEVICE_TYPE,
                additional_params_by_table_key=additional_params_by_table_key,
                parallel_requests=parallel_requests):
            # Note: all checks for validity of table_results_chunk are performed by the generator
            yield (device_type, table_result)

    # pylint: disable=arguments-differ
    def get_device_list(self,
                        parallel_requests=consts.DEFAULT_ASYNC_CHUNK_SIZE,
                        last_seen_timedelta: Optional[datetime.timedelta]=None,
                        use_dotwalking: bool=False,
                        dotwalking_per_request_limit: int=consts.DEFAULT_DOTWALKING_PER_REQUEST,
                        **_):
        # Note: use_dotwalking is only relevant to REST based ServiceNow Adapters
        for device_type, table_result in self._iter_device_table_chunks_by_details(
                parallel_requests=parallel_requests,
                last_seen_timedelta=last_seen_timedelta,
                use_dotwalking=use_dotwalking,
                dotwalking_per_request_limit=dotwalking_per_request_limit):
            yield device_type, table_result
