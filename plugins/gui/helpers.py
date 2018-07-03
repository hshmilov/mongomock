import logging
logger = logging.getLogger(f"axonius.{__name__}")
from axonius.plugin_base import add_rule, return_error
from flask import request, session
from axonius.utils.parsing import parse_filter
import pymongo
import json

# the maximal amount of data a pagination query will give
PAGINATION_LIMIT_MAX = 2000


# Caution! These decorators must come BEFORE @add_rule
def session_connection(func):
    """
    Decorator stating that the view requires the user to be connected
    """

    def wrapper(self, *args, **kwargs):
        user = session.get('user')
        if user is None:
            return return_error("You're not connected", 401)
        return func(self, *args, **kwargs)

    return wrapper


def add_rule_unauthenticated(rule, auth_method=session_connection, *args, **kwargs):
    """
    Syntactic sugar for add_rule(should_authenticate=False, ...)
    :param rule: rule name
    :param auth_method: An auth method
    :param args:
    :param kwargs:
    :return:
    """
    add_rule_res = add_rule(rule, should_authenticate=False, *args, **kwargs)
    if auth_method is not None:
        return lambda func: auth_method(add_rule_res(func))
    return add_rule_res


# Caution! These decorators must come BEFORE @add_rule
def filtered():
    """
    Decorator stating that the view supports ?filter='adapters == "active_directory_adapter"'
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            filter_obj = dict()
            try:
                filter_expr = request.args.get('filter')
                if filter_expr and filter_expr != "":
                    logger.debug("Parsing filter: {0}".format(filter_expr))
                    filter_obj = parse_filter(filter_expr)
            except Exception as e:
                return return_error("Could not create mongo filter. Details: {0}".format(e), 400)
            return func(self, mongo_filter=filter_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


def sorted_endpoint():
    """
    Decorator stating that the view supports ?sort=<field name><'-'/'+'>
    The field name must match a field in the collection to sort by
    and the -/+ determines whether sort is descending or ascending
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            sort_obj = {}
            try:
                sort_param = request.args.get('sort')
                desc_param = request.args.get('desc')
                if sort_param:
                    logger.info(f'Parsing sort: {sort_param}')
                    sort_obj[sort_param] = pymongo.DESCENDING if desc_param == '1' else pymongo.ASCENDING
            except Exception as e:
                return return_error("Could not create mongo sort. Details: {0}".format(e), 400)
            return func(self, mongo_sort=sort_obj, *args, **kwargs)

        return actual_wrapper

    return wrap


# Caution! These decorators must come BEFORE @add_rule
def projected():
    """
    Decorator stating that the view supports ?fields=["name","hostname",["os_type":"OS.type"]]
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            fields = request.args.get('fields')
            mongo_fields = None
            if fields:
                try:
                    mongo_fields = {}
                    for field in fields.split(","):
                        mongo_fields[field] = 1
                except json.JSONDecodeError:
                    pass
            return func(self, mongo_projection=mongo_fields, *args, **kwargs)

        return actual_wrapper

    return wrap


# Caution! These decorators must come BEFORE @add_rule
def paginated(limit_max=PAGINATION_LIMIT_MAX):
    """
    Decorator stating that the view supports "?limit=X&start=Y" for pagination
    """

    def wrap(func):
        def actual_wrapper(self, *args, **kwargs):
            # it's fine to raise here - an exception will be nicely JSONly displayed by add_rule
            limit = request.args.get('limit', limit_max, int)
            if limit < 0:
                raise ValueError("Limit mustn't be negative")
            if limit > limit_max:
                limit = limit_max
            skip = int(request.args.get('skip', 0, int))
            if skip < 0:
                raise ValueError("start mustn't be negative")
            return func(self, limit=limit, skip=skip, *args, **kwargs)

        return actual_wrapper

    return wrap
