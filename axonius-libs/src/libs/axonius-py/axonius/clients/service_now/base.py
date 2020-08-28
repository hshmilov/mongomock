import logging
from abc import abstractmethod, ABC

from typing import Optional, List, Dict, Tuple, Generator

from axonius.clients.service_now import consts

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

            # ADDITIONALLY, for users table key, configure username subtable as well
            if table_key == consts.USERS_TABLE_KEY:
                # Note: the check for 'name' vs the usage of 'user_name' was on the original sync impl.
                username = table_result.get('user_name')
                if not (table_result.get('name') and username):
                    return
                username_subtable = result_tables_by_key.setdefault(consts.USERS_USERNAME_KEY, dict())
                if username in username_subtable:
                    logger.debug(f'Located username duplication "{username}" in sub_table_key {table_key}')
                    return
                username_subtable[username] = table_result.get('sys_id')

        # CI_IPS - table = {'nic_dict.u_nic': [nic dicts...]}
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

        else:
            logger.error(f'Invalid table_key encountered {table_key}')
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

    def get_user_list(self, parallel_requests=consts.DEFAULT_ASYNC_CHUNK_SIZE):
        subtables_by_key = self._get_subtables_by_key(consts.USER_SUB_TABLES, parallel_requests=parallel_requests)

        # prepare users dict by sys_id
        tables_by_key = {}
        for table_key, table_result in self._iter_table_results_by_key({consts.USERS_TABLE_KEY: consts.USERS_TABLE},
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

            # add subtables
            user_to_yield[consts.SUBTABLES_KEY] = subtables_by_key
            yield user_to_yield

    @staticmethod
    def __get_table_name_by_device_type():
        return {table_details[consts.DEVICE_TYPE_NAME_KEY]: table_details[consts.TABLE_NAME_KEY]
                for table_details in consts.TABLES_DETAILS}

    def __iter_device_table_chunks_by_details(self, async_chunks: int = consts.DEFAULT_ASYNC_CHUNK_SIZE) \
            -> Generator[Tuple[str, str, List[dict]], None, None]:

        # prepare table_name_by_key for async requests
        table_name_by_device_type = self.__get_table_name_by_device_type()
        for device_type, table_result in self._iter_table_results_by_key(table_name_by_device_type,
                                                                         parallel_requests=async_chunks):
            # Note: all checks for validity of table_results_chunk are performed by the generator
            yield (device_type, table_name_by_device_type[device_type], table_result)

    # pylint: disable=arguments-differ
    def get_device_list(self,
                        fetch_users_info_for_devices=False,
                        fetch_ci_relations=False,
                        fetch_compliance_exceptions=False,
                        parallel_requests=consts.DEFAULT_ASYNC_CHUNK_SIZE):
        additional_params_by_table_key = {}
        sub_tables_to_request_by_key = consts.DEVICE_SUB_TABLES_KEY_TO_NAME.copy()

        if fetch_users_info_for_devices:
            sub_tables_to_request_by_key[consts.USERS_TABLE_KEY] = consts.USERS_TABLE

        if fetch_compliance_exceptions:
            sub_tables_to_request_by_key[consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE] = \
                consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE
            additional_params_by_table_key[consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE] = {
                'sysparm_fields': ','.join(consts.COMPLIANCE_EXCEPTION_TO_ASSET_TABLE_FIELDS)
            }
            sub_tables_to_request_by_key[consts.COMPLIANCE_EXCEPTION_DATA_TABLE] = \
                consts.COMPLIANCE_EXCEPTION_DATA_TABLE
            additional_params_by_table_key[consts.COMPLIANCE_EXCEPTION_DATA_TABLE] = {
                'sysparm_fields': ','.join(consts.COMPLIANCE_EXCEPTION_DATA_TABLE_FIELDS)
            }

        if fetch_ci_relations:
            sub_tables_to_request_by_key[consts.RELATIONS_TABLE] = consts.RELATIONS_TABLE
            additional_params_by_table_key[consts.RELATIONS_TABLE] = {
                'sysparm_fields': self._prepare_relations_fields()
            }

        subtables_by_key = self._get_subtables_by_key(sub_tables_to_request_by_key,
                                                      additional_params_by_table_key=additional_params_by_table_key,
                                                      parallel_requests=parallel_requests)
        self.__users_table = subtables_by_key.get(consts.USERS_TABLE_KEY) or {}
        for device_type, table_name, table_result in self.__iter_device_table_chunks_by_details(
                async_chunks=parallel_requests):

            yield {
                consts.TABLE_NAME_KEY: table_name,
                consts.DEVICE_TYPE_NAME_KEY: device_type,
                consts.DEVICES_KEY: [table_result],
                # Inject subtables to every table chunk
                # Note: '**' operator expands the dict into its individual items for addition in the new one.
                **subtables_by_key,
            }
