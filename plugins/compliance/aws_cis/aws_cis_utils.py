import logging
from functools import wraps

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
                logger.exception(f'Error checking rule {rule_section}')
                # args[0] == self
                args[0].report.add_rule_error(rule_section, f'Exception - {str(e)}')
        return wrapper
    return inner_function
