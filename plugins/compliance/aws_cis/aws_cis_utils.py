import logging
from functools import wraps
from typing import Optional, List

from axonius.entities import EntityType
from axonius.plugin_base import PluginBase

logger = logging.getLogger(f'axonius.{__name__}')
AWS_CIS_DEFAULT_REGION = 'us-east-1'


def get_api_error(data):
    return data.get('error')


def get_api_data(data):
    return data.get('data')


def good_api_response(data) -> dict:
    return {
        'status': 'ok',
        'data': data
    }


def bad_api_response(error) -> dict:
    return {
        'status': 'error',
        'error': error
    }


def aws_cis_rule(rule_section: str):
    def inner_function(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, rule_section=rule_section, **kwargs)
            except Exception as e:
                if 'An error occurred (AccessDenied)' not in str(e):
                    logger.exception(f'Error checking rule {rule_section}')
                else:
                    logger.debug(f'Permissions Error in checking rule {rule_section}')
                # args[0] == self
                args[0].report.add_rule_error(rule_section, f'Exception - {str(e)}')
        return wrapper
    return inner_function


def get_count_incompliant_cis_rule(
        entity: EntityType, account_id: Optional[int], cis_rule: str) -> int:
    if not account_id:
        return 0
    try:
        account_id = int(account_id)
    except Exception:
        return 0
    # pylint: disable=protected-access
    return PluginBase.Instance._entity_db_map[entity].find(
        {
            'adapters':
                {
                    '$elemMatch': {
                        '$and': [
                            {
                                'data.aws_cis_incompliant.rule_section': cis_rule,
                            },
                            {
                                'data.aws_account_id': account_id
                            }
                        ]
                    }
                }
        }
    ).count()


def errors_to_gui(errors: List[str]):
    return '\n'.join([f'- {x}' for x in errors])
