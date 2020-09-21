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


def cis_rule(rule_section: str):
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
        entity: EntityType, account_id: Optional[str], aws_cis_rule: str) -> int:
    if not account_id:
        return 0
    try:
        account_id = str(account_id)
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
                                'data.aws_cis_incompliant.rule_section': aws_cis_rule,
                            },
                            {
                                'data.aws_account_id': account_id
                            }
                        ]
                    }
                }
        }
    ).count()


def azure_cis_entities_by_subscription(subscription_names: List[str]):
    """
    Build query terms to match entities with any of the (unique) listed subscription names
    :param subscription_names: list of subscription names. Duplicates are removed.
    :return: Dict with mongoDB formatted query for matching with subscription_names using the OR clause.
    """
    if isinstance(subscription_names, str):
        subscription_names = [subscription_names]
    subscription_names = set(subscription_names)
    list_subs = list(
        {'data.subscription_name': str(sub_name)} for sub_name in subscription_names
    )
    return {'$or': list(list_subs)} if subscription_names else {}


def get_count_incompliant_azure_cis_rule(entity: EntityType,
                                         azure_cis_rule: str,
                                         account_id: Optional[str] = None,
                                         subscription_names: Optional[List[str]] = None) -> int:
    """
    Query and count entities that match the rule section and one or both of azure_account_id and any of the
    subscription names
    :param entity: EntityType.Device or EntityType.User
    :param azure_cis_rule: Rule section according to benchmark, e.g. "1.2"
    :param account_id: (optional) Account ID string, in format "accountTag_tenantID" (exact match)
    :param subscription_names: (optional) list of subscription names to filter for (match any)
    :return: int count of entities matching the parameters
    """
    if not (account_id or subscription_names):
        return 0

    # Initialize query terms list + add basic term
    query_terms = [
        {
            'data.azure_cis_incompliant.rule_section': azure_cis_rule,
        },
    ]
    # Match for account id if specified
    if account_id:
        try:
            account_id = str(account_id)
        except Exception:
            return 0
        query_terms.append({
            'data.azure_account_id': account_id
        })
    # Match for subscription names if specified
    if subscription_names:
        sub_terms = azure_cis_entities_by_subscription(subscription_names)
        if sub_terms:
            query_terms.append(sub_terms)

    logger.debug(f'Query terms: {query_terms}')
    # Execute the query and return count of results
    # pylint: disable=protected-access
    return PluginBase.Instance._entity_db_map[entity].find(
        {
            'adapters':
                {
                    '$elemMatch': {
                        '$and': query_terms
                    }
                }
        }
    ).count()


def build_entities_query(entity_type: str,
                         rule_section: str,
                         account_id: Optional[str] = None,
                         subscription_names: Optional[List[str]] = None,
                         plugin_name: str = 'azure_adapter',
                         field_prefix: str = 'azure'
                         ):
    """
    Build a query to get affected devices.
    Note: at least one of account_id or subscription_names must be specified.
    XXX In future refactor/dev it is recommended to convert all affected_devices queries to use this method.
    :param entity_type: 'devices' or 'users'
    :param rule_section: Rule section to search for
    :param account_id: Account id to search for, or empty string (optional) - leave None to omit entirely
    :param subscription_names: match IN subscription names (optional) - leave None or keep empty to omit entirely
    :param plugin_name: plugin name of adapter to search in (default 'azure_adapter')
    :param field_prefix: prefix of specific data fields (default 'azure')
    :return: dictionary for AQL query
    """
    queries_list = [
        f'(plugin_name == \'{plugin_name}\')',
        f'(data.{field_prefix}_cis_incompliant.rule_section == "{rule_section}")'
    ]
    # We do not want to query for ALL accounts
    if not (account_id or subscription_names):
        logger.warning(f'Attempted to query entities without specifying either account_id or subscription_names')
        return None

    if account_id is not None:  # account ID could be empty string
        queries_list.append(f'(data.{field_prefix}_account_id == "{account_id or ""}")')

    if subscription_names:
        if isinstance(subscription_names, str):  # in case a single string is passed
            subscription_names = [subscription_names]
        if isinstance(subscription_names, list):
            subscription_names = set(subscription_names)  # Eliminate duplicates
            subs_str = ', '.join((f'"{sub_name}"' for sub_name in subscription_names))
            queries_list.append(f'(data.subscription_name in [{subs_str}])')

    # build and return complete query
    return {
        'type': entity_type,
        'query': f'specific_data == match([{" and ".join(queries_list)}])'
    }


def errors_to_gui(errors: List[str]):
    return '\n'.join([f'- {x}' for x in errors])
