import logging
import functools
import re
import time
from typing import List

from bson import ObjectId
from flask import (request)
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError

from axonius.plugin_base import limiter, ratelimiting_settings
from axonius.consts.gui_consts import (DASHBOARD_LIFECYCLE_ENDPOINT, SKIP_ACTIVITY_ARG, ACTIVITY_PARAMS_ARG,
                                       USERS_COLLECTION, ROLES_COLLECTION, LAST_UPDATED_FIELD)
from axonius.consts.metric_consts import ApiMetric, SystemMetric
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import PluginBase, return_error
from axonius.utils.gui_helpers import (add_rule_custom_authentication, log_activity_rule)
from axonius.utils.metric import remove_ids
from axonius.utils.permissions_helper import (PermissionCategory,
                                              PermissionAction,
                                              PermissionValue,
                                              is_axonius_role)
from gui.logic.filter_utils import filter_archived
from gui.logic.db_helpers import translate_role_id_to_role, decode_datetime, \
    translate_user_to_details
from gui.logic.login_helper import get_user_for_session

# pylint: disable=keyword-arg-before-vararg,invalid-name,redefined-builtin,too-many-instance-attributes, no-member, protected-access

logger = logging.getLogger(f'axonius.{__name__}')


def session_connection(func,
                       required_permission: PermissionValue,
                       enforce_trial=True,
                       enforce_session=True,
                       enforce_permissions=True,
                       proceed_and_set_access=False,
                       support_internal_api_key=False):
    """
    Decorator stating that the view requires the user to be connected

    :param func: the method to decorate
    :param required_permission: The Permission required for this api call or none
    :param enforce_trial: Restrict if system has a trial expiration date configured and it has passed
    :param enforce_session: if this endpoint requires a login
    :param enforce_permissions: if this endpoint need a permission
    :param proceed_and_set_access: Skip error logging in case there are missing permissions
    If set to true, the decorator won't generate an error but instead sends an argument "no_access" to the
    wrapped function, and the error handling should be done there instead.
    :param support_internal_api_key: use only the api key instead of the session login - for plugin connections
    :return:
    """
    # pylint: disable=too-many-return-statements, too-many-branches

    def wrapper(self, *args, **kwargs):
        is_api_key_internal = support_internal_api_key and request.headers.get('x-api-key')
        is_api_user = False
        if enforce_session and not is_api_key_internal:
            user = None
            if request.headers.get('api-key') and request.headers.get('api-secret'):
                current_user = check_auth_api_key(request.headers['api-key'], request.headers['api-secret'])
                if current_user:
                    PluginBase.Instance.set_current_user(current_user)
                    is_api_user = True
                    user = PluginBase.Instance.get_user
            else:
                try:
                    verify_jwt_in_request()
                except NoAuthorizationError:
                    return return_error('Not logged in', 401)
                jwt_user = get_jwt_identity()
                user_info = translate_user_to_details(jwt_user.get('user_name'), jwt_user.get('source'))
                role = translate_role_id_to_role(ObjectId(user_info.role_id))
                user_last_updated = max([user_info.last_updated, role.last_updated])
                if user_last_updated > decode_datetime(jwt_user.get(LAST_UPDATED_FIELD)):
                    return return_error('Your user was updated and your token is invalid', 401)
                PluginBase.Instance.set_current_user(jwt_user)
                user = PluginBase.Instance.get_user

            if user is None:
                return return_error('Not logged in', 401)

            if enforce_permissions:
                is_expired = PluginBase.Instance.trial_expired() or PluginBase.Instance.contract_expired()
                is_blocked = (enforce_trial and is_expired) and not is_axonius_role(user)
                is_not_permitted = not check_permissions(user.get('permissions'), required_permission)
                if (is_not_permitted and not proceed_and_set_access) or is_blocked:
                    return return_error('You are lacking some permissions for this request', 401)
                # If continue on error is set, we return a new argument indicating whether or not we have access
                if proceed_and_set_access:
                    kwargs['no_access'] = is_not_permitted

        log_request(is_api_user)
        now = time.time()
        try:
            return func(self, *args, **kwargs)
        finally:
            log_request_duration(now)

    return wrapper


def log_request(api_request):
    method = request.method
    cleanpath = remove_ids(request.path)
    if api_request:
        log_metric(logger, ApiMetric.PUBLIC_REQUEST_PATH, cleanpath, method=method)
    elif method != 'GET':
        log_metric(logger, ApiMetric.REQUEST_PATH, cleanpath, method=method)


def log_request_duration(start_time):
    # don't change these consts since we monitor this our alerts systems
    if request.args.get('is_refresh') != '1' and DASHBOARD_LIFECYCLE_ENDPOINT not in request.path:
        cleanpath = remove_ids(request.path)
        delay_seconds = time.time() - start_time
        if delay_seconds > 1:
            log_metric(logger, SystemMetric.TIMED_ENDPOINT,
                       metric_value=delay_seconds,
                       endpoint=cleanpath,
                       method=request.method)


class gui_category_add_rules:
    def __init__(self, rule='', permission_category: PermissionCategory = None):
        """
        The decorator for a class that contains url with login and permissions for each url
        This decorator creates the rules in the server
        :param rule:
        :param permission_category: the PermissionCategory of the class
        """
        self.rule = rule
        self.permission_category = permission_category
        if self.rule and self.permission_category is None and PermissionCategory.has_value(self.rule):
            self.permission_category = PermissionCategory(self.rule)

    def __get__(self, obj, type=None):
        return functools.partial(self, obj)

    def __call__(self, cls, *args, **kwargs):
        cls.rule = self.rule
        cls.permission_category = self.permission_category

        if hasattr(cls, 'permission_section'):
            setattr(cls, 'permission_section', None)

        def add_function_rule(original_cls,
                              method_name,
                              is_section,
                              base_rule,
                              base_permission_category,
                              inner_kwargs):
            """
            Add the url rule for the method
            :param original_cls:
            :param method_name: The method name
            :param is_section: If the current method belongs to a sub category
            :param base_rule: the rule of the category
            :param base_permission_category: the pr
            :param inner_kwargs:
            """
            func = original_cls.__dict__[method_name]

            # if this method is not an endpoint
            if not hasattr(func, 'endpoint_args'):
                return

            current_args = func.endpoint_args
            permission_category = None
            permission_section = None
            if is_section and base_permission_category:
                # if this method is in a section
                permission_category = base_permission_category
            elif original_cls.permission_category:
                # if this method is in a category
                permission_category = original_cls.permission_category

            if is_section and original_cls:
                # if the class is a section than take if from the class definition
                permission_section = original_cls.permission_section

            prefix = []
            if base_rule:
                prefix.append(base_rule)
            if original_cls.rule:
                prefix.append(original_cls.rule)
            if current_args.rule:
                prefix.append(current_args.rule)
            custom_rule = '/'.join(prefix)

            required_permission = current_args.required_permission
            # If no explicit permission requirement, create from class categories
            if not required_permission and (permission_category or permission_section):
                # If rule is defined as a permission, use it
                # Otherwise, request.method of the call will be used
                required_permission = PermissionValue.get(
                    PermissionAction(current_args.rule) if PermissionAction.has_value(
                        current_args.rule) else None,
                    permission_category,
                    permission_section)

            def session_connection_permissions(*args, **kwargs):
                return session_connection(*args, **kwargs,
                                          required_permission=required_permission,
                                          enforce_trial=current_args.enforce_trial,
                                          enforce_session=current_args.enforce_session,
                                          enforce_permissions=current_args.enforce_permissions,
                                          proceed_and_set_access=current_args.proceed_and_set_access,
                                          support_internal_api_key=current_args.support_internal_api_key)

            methods = current_args.kwargs.get('methods') or ('GET',)
            fn = add_rule_custom_authentication(custom_rule, session_connection_permissions,
                                                current_args.support_internal_api_key,
                                                methods=methods)
            # Defining a new name that includes the rul for the method
            # in case there are more than 1 method with the same name
            new_function_name = f'{custom_rule}_{method_name}'
            func.__name__ = new_function_name
            new_function = fn(*(func,), **inner_kwargs)
            new_function.__name__ = new_function_name
            if current_args.enforce_session and not current_args.kwargs.get(SKIP_ACTIVITY_ARG):

                activity_category = original_cls.rule if not base_rule else f'{base_rule}.{original_cls.rule}' \
                    .replace('/', '.')
                new_function = log_activity_rule(current_args.rule,
                                                 activity_category,
                                                 current_args.kwargs.get(ACTIVITY_PARAMS_ARG))(new_function)
            if current_args.limiter_key_func and current_args.shared_limit_scope:
                new_function = limiter.shared_limit(ratelimiting_settings,
                                                    key_func=current_args.limiter_key_func,
                                                    scope=current_args.shared_limit_scope)(new_function)
            setattr(cls, new_function_name, new_function)

        for name in list(cls.__dict__):
            add_function_rule(cls, name, False, None, None, kwargs)

        for child_class in cls.__bases__:
            if not hasattr(child_class, 'permission_section'):
                continue
            for name in list(child_class.__dict__):
                add_function_rule(child_class, name, True,
                                  cls.rule, cls.permission_category, kwargs)

        return cls


class gui_section_add_rules:
    def __init__(self, rule='', permission_section: PermissionCategory = None):
        """
        The decorator for a section class that contains url with login and permissions for each url
        :param rule:
        :param permission_section: the PermissionCategory of the class
        """
        self.rule = rule
        self.permission_section = permission_section

        if self.rule and self.permission_section is None and PermissionCategory.has_value(self.rule):
            self.permission_section = PermissionCategory(self.rule)

    def __get__(self, obj, type=None):
        return functools.partial(self, obj)

    def __call__(self, cls, *args, **kwargs):
        cls.rule = self.rule
        cls.permission_section = self.permission_section
        return cls


class gui_route_logged_in:
    def __init__(self,
                 rule='',
                 required_permission: PermissionValue = None,
                 enforce_trial=True,
                 enforce_session=True,
                 enforce_permissions=True,
                 proceed_and_set_access=False,
                 support_internal_api_key=False,
                 limiter_key_func=None,
                 shared_limit_scope=None,
                 *args, **kwargs):
        """
        The decorator for adding endpoints on methods (only for categories or sections)
        :param rule: The suffix of the url of the endpoint
        :param required_permission: the required permission values:
        a list of Tuples each containing the permission action, the category and if needed the section
        :param enforce_trial: Should this endpoint work when trial is over
        :param enforce_session: Should this endpoint work only when this caller has a valid session
        :param enforce_permissions: Should this endpoint work only when this session has the right permissions
        :param proceed_and_set_access: Should the error reporting be skipped in case there are missing permissions.
        If set to true, the decorator won't generate an error but instead sends an argument "no_access" to the
        wrapped function, and the error handling should be done there instead.
        :param support_internal_api_key: Should this endpoint work
        when the internal caller use the api key instead on session
        :param args:
        :param kwargs:
        """
        self.rule = rule
        self.required_permission = required_permission
        self.enforce_trial = enforce_trial
        self.enforce_session = enforce_session
        self.enforce_permissions = enforce_permissions
        self.proceed_and_set_access = proceed_and_set_access
        self.support_internal_api_key = support_internal_api_key
        self.limiter_key_func = limiter_key_func
        self.shared_limit_scope = shared_limit_scope
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        fn = args[0]
        fn.endpoint_args = self
        return fn


def is_valid_node_hostname(hostname):
    """
    verify hostname is a valid lnx hostname pattern .
    """
    if not hostname:
        return False
    if len(hostname) > 255:
        return False
    if hostname[-1] == '.':
        hostname = hostname[:-1]
    # pylint: disable=C4001,W1401
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split('.'))


def check_permissions(user_permissions: dict,
                      required_permission: PermissionValue) -> bool:
    """
    Checks whether user_permissions has all required_permissions

    :param user_permissions: Dictionary of the current user's permissions -
                             PermissionCategory and PermissionAction keys and boolean for values
    Example:
    {
        PermissionCategory.settings: {
            PermissionAction.View: True,
            PermissionCategory.Users: {
                PermissionAction.Add: True,
                PermissionAction.Edit: False,
            },
            ...
        }
    }
    :param required_permission: The PermissionValue required for the endpoint
    :return: Whether or not user has the permission
    """
    has_category = required_permission.Category or required_permission.Section
    if not required_permission.Action and PermissionAction(request.method.lower()) and has_category:
        # If permission action not defined then take it from the request method
        required_permission = PermissionValue.get(PermissionAction(request.method.lower()),
                                                  required_permission.Category,
                                                  required_permission.Section)
    if required_permission:
        clean_categories = [category for category
                            in [required_permission.Category, required_permission.Section] if category]
        current_category = get_permissions_action_category(user_permissions, clean_categories)
        if not current_category or (not current_category.get(required_permission.Action)):
            return False
    return True


def check_auth_api_key(api_key, api_secret):
    """
    This function is called to check if an api key and secret match
    """
    users_collection = PluginBase.Instance._get_collection(USERS_COLLECTION)
    roles_collection = PluginBase.Instance._get_collection(ROLES_COLLECTION)

    user_from_db = users_collection.find_one(filter_archived({
        'api_key': api_key,
        'api_secret': api_secret
    }))

    if not user_from_db:
        return None

    role = roles_collection.find_one({'_id': user_from_db.get('role_id')})
    return get_user_for_session(user_from_db, role, is_api_user=True)


def get_permissions_action_category(permissions: dict,
                                    categories: List[PermissionCategory]) -> dict:
    """
    Get the leaf category with the permission actions
    :param permissions: the current user permissions category
    :param categories: the level of categories for the current action
    :return:
    """
    if not categories or not isinstance(permissions, dict):
        return permissions
    return get_permissions_action_category(permissions[categories[0]], categories[1:])
