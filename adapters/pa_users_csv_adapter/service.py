import logging
from collections import defaultdict

from axonius.adapter_exceptions import ClientConnectionException

from axonius.utils.json import to_json, from_json

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.consts import remote_file_consts
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import make_dict_from_csv
from axonius.utils.remote_file_utils import (load_remote_data,
                                             test_file_reachability)

logger = logging.getLogger(f'axonius.{__name__}')


class FwRuleEntry(SmartJsonClass):
    rule_no = Field(str, 'Rule Number')
    rule_name = Field(str, 'Rule Name')
    src_addr = Field(str, 'Source Address')
    dst_addr = Field(str, 'Destination Address')
    hip_profiles = Field(str, 'HIP Profiles')
    app = Field(str, 'Application')
    svc = Field(str, 'Service')
    action = Field(str, 'Action')
    profiles = Field(str, 'Profiles')
    disabled = Field(bool, 'Disabled')


class PaUsersCsvAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyUserAdapter(UserAdapter):
        file_name = Field(str, 'CSV File Name')
        fw_rule_entries = ListField(FwRuleEntry, 'Entries')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return f'wix_fw_{client_config["user_id"]}'

    @staticmethod
    def _test_reachability(client_config):
        return test_file_reachability(client_config)

    # pylint: disable=arguments-differ
    @staticmethod
    def _connect_client(client_config):
        filename, csv_data = load_remote_data(client_config)
        try:
            make_dict_from_csv(csv_data)
        except Exception as e:
            raise ClientConnectionException(f'Failed to load csv data: {str(e)}')
        return client_config

    @staticmethod
    def _query_users_by_client(key, data):
        """
        Get all users from a specific csv file

        :param str key: The name of the client
        :param obj data: The data that

        :return: A json with all the attributes returned from the Server
        """
        file_name, csv_data = load_remote_data(data)
        csv_dict = make_dict_from_csv(csv_data)
        return file_name, csv_dict

    @staticmethod
    def _clients_schema():
        """
        The schema PaUsersCsvAdapter expects from configs

        :return: JSON scheme
        """
        return {
            'items': [
                *remote_file_consts.FILE_CLIENTS_SCHEMA
            ],
            'required': [
                *remote_file_consts.FILE_SCHEMA_REQUIRED
            ],
            'type': 'array'
        }

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, users_info):
        if not users_info:
            return
        file_name, users_raw_list = users_info
        if not file_name or not users_raw_list:
            return
        # Nestify duplicates into a dict
        users_raw = defaultdict(list)
        for user_entry_raw in users_raw_list:
            try:
                user_id = user_entry_raw['User']
                users_raw[user_id].append(user_entry_raw)
            except Exception as e:
                logger.warning(f'Got {str(e)} trying to parse user from {user_entry_raw}')
                continue
        for user_name, user_raw in users_raw.items():
            try:
                user = self._new_user_adapter()
                if not user_name:
                    logger.error(f'Bad user with no ID: {user_raw}')
                # generic fields
                user.id = user_name
                user.mail = user_name
                user.username = user_name
                # specific fields
                rule_entries = list()
                for entry in user_raw:
                    try:
                        rule_entries.append(FwRuleEntry(
                            rule_no=entry.get('RuleNumber'),
                            rule_name=entry.get('RuleName'),
                            src_addr=entry.get('SourceAddress'),
                            dst_addr=entry.get('DestAddress'),
                            hip_profiles=entry.get('HipProfiles'),
                            app=entry.get('Application'),
                            svc=entry.get('Service'),
                            action=entry.get('Action'),
                            profiles=entry.get('Profiles'),
                            disabled=entry.get('Disabled', '').lower() == 'yes'
                        ))
                    except Exception as e:
                        logger.warning(f'Got {str(e)} trying to parse rule entry {entry}')
                        continue
                user.fw_rule_entries = rule_entries
                user.file_name = file_name
                user.set_raw(from_json(to_json({user_name: user_raw})))
                yield user
            except Exception:
                logger.exception(f'Problem adding user: {user_name}:{str(user_raw)}')
        # end for

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.UserManagement, AdapterProperty.Firewall]
