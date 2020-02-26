import os
import logging
import time
from typing import Iterable
from bson import ObjectId

from flask import (has_request_context, request, session)

from axonius.consts.gui_consts import (DASHBOARD_LIFECYCLE_ENDPOINT)
from axonius.consts.metric_consts import ApiMetric, SystemMetric
from axonius.consts.plugin_consts import (AXONIUS_USER_NAME,)
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import PluginBase, return_error
from axonius.utils.gui_helpers import (Permission,
                                       check_permissions,
                                       add_rule_custom_authentication)
from axonius.utils.metric import remove_ids
from gui.okta_login import OidcData
# pylint: disable=keyword-arg-before-vararg,invalid-name

logger = logging.getLogger(f'axonius.{__name__}')


def session_connection(func, required_permissions: Iterable[Permission], enforce_trial=True):
    """
    Decorator stating that the view requires the user to be connected
    :param func: the method to decorate
    :param required_permissions: The set (or list...) of Permission required for this api call or none
    :param enforce_trial: Restrict if system has a trial expiration date configure and it has passed
    """

    def wrapper(self, *args, **kwargs):
        if os.environ.get('HOT') == 'true':
            # pylint: disable=W0603
            global session
            user_db = {'_id': ObjectId(), 'user_name': 'admin', 'admin': True,
                       'permissions': {}}
            session = {'user': user_db}

        user = session.get('user')
        if user is None:
            return return_error('You are not connected', 401)
        permissions = user.get('permissions')
        is_expired = enforce_trial and \
            (PluginBase.Instance.trial_expired() or PluginBase.Instance.contract_expired()) and \
            user.get('user_name') != AXONIUS_USER_NAME
        is_not_permitted = not check_permissions(permissions, required_permissions, request.method) \
            and not user.get('admin')
        if is_not_permitted or is_expired:
            return return_error('You are lacking some permissions for this request', 401)

        oidc_data: OidcData = session.get('oidc_data')
        if oidc_data:
            try:
                oidc_data.beautify()
            except Exception:
                # TBD: Which exception exactly are raised
                session['user'] = None
                return return_error('Your OIDC sessions has expired', 401)

        if has_request_context():
            path = request.path
            cleanpath = remove_ids(path)
            method = request.method
            if method != 'GET':
                log_metric(logger, ApiMetric.REQUEST_PATH, cleanpath, method=request.method)

        now = time.time()
        try:
            return func(self, *args, **kwargs)
        finally:
            if has_request_context():
                # don't change these consts since we monitor this our alerts systems
                if request.args.get('is_refresh') != '1' and DASHBOARD_LIFECYCLE_ENDPOINT not in request.path:
                    cleanpath = remove_ids(request.path)
                    delay_seconds = time.time() - now
                    if delay_seconds > 1:
                        log_metric(logger, SystemMetric.TIMED_ENDPOINT,
                                   metric_value=delay_seconds,
                                   endpoint=cleanpath,
                                   method=request.method)

    return wrapper


# Caution! These decorators must come BEFORE @add_rule
def gui_add_rule_logged_in(rule, required_permissions: Iterable[Permission] = None, enforce_trial=True,
                           *args, **kwargs):
    """
    A URL mapping for GUI endpoints that use the browser session for authentication,
    see add_rule_custom_authentication for more information.
    :param rule: the url that calls this method
    :param required_permissions: see session_connection for docs
    :param enforce_trial: Should enforce trial be checked and enforce it if it does
    """
    required_permissions = set(required_permissions or [])

    def session_connection_permissions(*args, **kwargs):
        return session_connection(*args, **kwargs, required_permissions=required_permissions,
                                  enforce_trial=enforce_trial)

    return add_rule_custom_authentication(rule, session_connection_permissions, *args, **kwargs)


def is_valid_node_hostname(hostname):
    """
    verify hostname is a valid lnx hostname pattern .
    """
    import re
    if len(hostname) > 255:
        return False
    if hostname[-1] == '.':
        hostname = hostname[:-1]
    # pylint: disable=C4001,W1401
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split('.'))
