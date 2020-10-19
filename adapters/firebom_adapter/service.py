import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.consts import remote_file_consts
from axonius.utils.files import get_local_config_file
from axonius.utils.json import from_json
from axonius.utils.parsing import get_exception_string
from axonius.utils.remote_file_utils import load_remote_data, test_file_reachability
from firebom_adapter.client_id import get_client_id

logger = logging.getLogger(f'axonius.{__name__}')


class FirebomAdapter(AdapterBase):
    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return test_file_reachability(client_config)

    def _connect_client(self, client_config):
        try:
            file_name, file_data = load_remote_data(client_config)
            try:
                json_data = from_json(file_data)
            except Exception as e:
                logger.exception(f'File is not a valid JSON')
                raise ValueError(f'File is not a valid JSON: {str(e)}')

            if not isinstance(json_data, dict) or not isinstance(json_data.get('falcon_instance'), dict):
                raise ValueError(f'Expecting JSON to have a dictionary with key "falcon_instance"')

            if not isinstance(json_data.get('falcon_instance', {}).get('functional_domains'), list):
                raise ValueError(f'Missing key "functional_domains" inside "falcon_instance"')

            return json_data
        except Exception:
            logger.exception(f'Error connecting Firebom')
            raise ClientConnectionException(get_exception_string(force_show_traceback=True))

    def _query_devices_by_client(self, client_name: str, client_data: dict):
        # This adapter is not yielding any devices. It is just parsing them and uploading them as a key-val dictionary.
        if not isinstance(client_data.get('falcon_instance'), dict):
            raise ValueError(f'Warning - invalid key "falcon_instance"')

        root = client_data['falcon_instance']

        if not isinstance(root.get('functional_domains'), list):
            raise ValueError(f'Warning - invalid key "functional_domains"')

        service_team_name_to_service_team = dict()
        service_team_name_to_service_instance = dict()
        account_id_to_service_team_name = dict()

        for functional_domain in root['functional_domains']:
            for service_team in (functional_domain.get('service_teams') or []):
                service_team_name = service_team.get('name')
                account_id = service_team.get('account_id')

                if not account_id or not service_team_name:
                    logger.warning(f'Warning - no account id or service team name, continuing')
                    continue

                service_team_name_to_service_team[service_team_name] = service_team
                if account_id not in account_id_to_service_team_name:
                    account_id_to_service_team_name[account_id] = []
                account_id_to_service_team_name[account_id].append(service_team_name)

            for service_instance in (functional_domain.get('service_instances') or []):
                service_team = service_instance.get('service_team')
                if not service_team:
                    logger.warning(f'Warning - no service team key for service instance, continuing')
                    continue

                if service_team not in service_team_name_to_service_instance:
                    service_team_name_to_service_instance[service_team] = []
                service_team_name_to_service_instance[service_team].append(service_instance)

        logger.info(f'Successfully parsed {len(account_id_to_service_team_name.keys())} account_ids')
        logger.info(f'Successfully parsed {len(service_team_name_to_service_team.keys())} service teams')

        self.set_global_keyval('firebom_service_team_name_to_service_team', service_team_name_to_service_team)
        self.set_global_keyval('firebom_service_team_name_to_service_instance', service_team_name_to_service_instance)
        self.set_global_keyval('firebom_account_id_to_service_team_name', account_id_to_service_team_name)
        return []

    def _parse_raw_data(self, devices_raw_data):
        yield from []

    @staticmethod
    def _clients_schema():
        """
        The schema FirebomAdapter expects from configs

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

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
