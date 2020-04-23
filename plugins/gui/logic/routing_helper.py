import logging
import functools
import re
import time
from typing import List

from flask import (request, session)

from axonius.plugin_base import limiter, ratelimiting_settings
from axonius.consts.gui_consts import (DASHBOARD_LIFECYCLE_ENDPOINT, CSRF_TOKEN_LENGTH, EXCLUDED_CSRF_ENDPOINTS,
                                       SKIP_ACTIVITY_ARG, ACTIVITY_PARAMS_ARG)
from axonius.consts.metric_consts import ApiMetric, SystemMetric
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import PluginBase, return_error, random_string
from axonius.utils.gui_helpers import (add_rule_custom_authentication, log_activity_rule)
from axonius.utils.metric import remove_ids
from axonius.utils.permissions_helper import (PermissionCategory,
                                              PermissionAction,
                                              PermissionValue,
                                              is_axonius_role)
from gui.okta_login import OidcData

# pylint: disable=keyword-arg-before-vararg,invalid-name,redefined-builtin

logger = logging.getLogger(f'axonius.{__name__}')


def session_connection(func,
                       required_permission: PermissionValue,
                       enforce_trial=True,
                       enforce_session=True,
                       enforce_permissions=True,
                       enforce_api_key=False):
    """
    Decorator stating that the view requires the user to be connected
    And also to validate the csrf token and generate
    new one before the actual desired action of the request happens
    The CSRF token is being validated only to POST, PUT, DELETE, PATCH requests and only.
    Any other GET request, failed CSRF Validation or success CSRF validation will cause new token generation.

    :param func: the method to decorate
    :param required_permission: The Permission required for this api call or none
    :param enforce_trial: Restrict if system has a trial expiration date configured and it has passed
    :param enforce_session: if this endpoint requires a login
    :param enforce_permissions: if this endpoint need a permission
    :param enforce_api_key: use the api key instead of the session login
    :return:
    """
    # pylint: disable=too-many-return-statements, too-many-branches

    def wrapper(self, *args, **kwargs):
        enforce_by_api_key = enforce_api_key and request.headers.get('x-api-key')
        if enforce_session and not enforce_by_api_key:
            user = session.get('user') if session else None
            if user is None:
                return return_error('You are not connected', 401)

            if enforce_permissions:
                is_expired = PluginBase.Instance.trial_expired() or PluginBase.Instance.contract_expired()
                is_blocked = (enforce_trial and is_expired) and not is_axonius_role(user)
                is_not_permitted = not check_permissions(user.get('permissions'), required_permission)
                if is_not_permitted or is_blocked:
                    return return_error('You are lacking some permissions for this request', 401)
                oidc_data: OidcData = session.get('oidc_data')
                if oidc_data:
                    try:
                        oidc_data.beautify()
                    except Exception:
                        # TBD: Which exception exactly are raised
                        session['user'] = None
                        return return_error('Your OIDC sessions has expired', 401)

        # We handle only submitted forms with session, therefore only POST, PUT, DELETE, PATCH are in our interest
        # Dont check CSRF during frontend debug
        if not (request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE') or not session):
            try:
                csrf_token_header = request.headers.get('X-CSRF-TOKEN', None)
                if 'csrf-token' in session:
                    csrf_token = session['csrf-token']
                    if csrf_token is not None and request.path not in EXCLUDED_CSRF_ENDPOINTS and \
                            csrf_token != csrf_token_header:
                        return return_error('Bad CSRF-Token', 403)
                    # Success token comparison or first session after login, no token twice
                    if session['user'] is not None:
                        session['csrf-token'] = random_string(CSRF_TOKEN_LENGTH)
                # This should never happen to authenticated user with active session...
                else:
                    return return_error('No CSRF-Token in session', 403)
            except Exception as e:
                logger.error(e)
                session['csrf-token'] = random_string(CSRF_TOKEN_LENGTH)
                return return_error(str(e), non_prod_error=True, http_status=403)

        log_request()
        now = time.time()
        try:
            return func(self, *args, **kwargs)
        finally:
            log_request_duration(now)

    return wrapper


def log_request():
    method = request.method
    if method != 'GET':
        log_metric(logger, ApiMetric.REQUEST_PATH, remove_ids(request.path), method=method)


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
                permission_action = PermissionAction(current_args.rule) if PermissionAction.has_value(
                    current_args.rule) else None
                required_permission = PermissionValue.get(permission_action, permission_category, permission_section)

            def session_connection_permissions(*args, **kwargs):
                return session_connection(*args, **kwargs,
                                          required_permission=required_permission,
                                          enforce_trial=current_args.enforce_trial,
                                          enforce_session=current_args.enforce_session,
                                          enforce_permissions=current_args.enforce_permissions,
                                          enforce_api_key=current_args.enforce_api_key)

            methods = current_args.kwargs.get('methods') or ('GET',)
            fn = add_rule_custom_authentication(custom_rule, session_connection_permissions,
                                                current_args.enforce_api_key,
                                                methods=methods)
            # Defining a new name that includes the rul for the method
            # in case there are more than 1 method with the same name
            new_function_name = f'{custom_rule}_{method_name}'
            func.__name__ = new_function_name
            new_function = fn(*(func,), **inner_kwargs)
            new_function.__name__ = new_function_name
            if current_args.enforce_session and not current_args.kwargs.get(SKIP_ACTIVITY_ARG):
                activity_category = original_cls.rule if not base_rule else f'{base_rule}.{original_cls.rule}'
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
                 enforce_api_key=False,
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
        :param enforce_api_key: Should this endpoint work when the caller use the api key instead on session
        :param args:
        :param kwargs:
        """
        self.rule = rule
        self.required_permission = required_permission
        self.enforce_trial = enforce_trial
        self.enforce_session = enforce_session
        self.enforce_permissions = enforce_permissions
        self.enforce_api_key = enforce_api_key
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
