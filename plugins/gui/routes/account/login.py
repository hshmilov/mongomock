import json
import logging
import os

from datetime import datetime
from bson import ObjectId
import ldap3
from flask import (jsonify,
                   make_response, redirect, request, session)
from werkzeug.wrappers import Response
from urllib3.util.url import parse_url
from passlib.hash import bcrypt
from flask_limiter.util import get_remote_address
# pylint: disable=import-error,no-name-in-module
from onelogin.saml2.auth import OneLogin_Saml2_Auth


from axonius.clients.ldap.exceptions import LdapException
from axonius.clients.ldap.ldap_connection import LdapConnection
from axonius.clients.rest.connection import RESTConnection
from axonius.consts.gui_consts import (CSRF_TOKEN_LENGTH, LOGGED_IN_MARKER_PATH, PREDEFINED_FIELD, IS_AXONIUS_ROLE,
                                       PREDEFINED_ROLE_RESTRICTED)
from axonius.clients.rest.exception import RESTException
from axonius.consts.metric_consts import SystemMetric
from axonius.consts.plugin_consts import (CONFIGURABLE_CONFIGS_COLLECTION,
                                          GUI_PLUGIN_NAME)
from axonius.logging.audit_helper import AuditCategory, AuditAction, AuditType
from axonius.logging.metric_helper import log_metric
from axonius.plugin_base import return_error, random_string, LIMITER_SCOPE
from axonius.types.ssl_state import (SSLState)
from axonius.utils.parsing import bytes_image_to_base64
from axonius.utils.permissions_helper import deserialize_db_permissions, is_axonius_role
from gui.logic.filter_utils import filter_archived
from gui.logic.login_helper import has_customer_login_happened
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.logic.users_helper import beautify_user_entry
from gui.okta_login import try_connecting_using_okta
# pylint: disable=no-member,too-many-boolean-expressions,too-many-return-statements,no-self-use,no-else-return,too-many-branches,too-many-locals

logger = logging.getLogger(f'axonius.{__name__}')


@gui_category_add_rules('')
class Login:

    @gui_route_logged_in('get_login_options', enforce_session=False)
    def get_login_options(self):
        return jsonify({
            'okta': {
                'enabled': self._okta['enabled'],
                'client_id': self._okta['client_id'],
                'url': self._okta['url'],
                'gui2_url': self._okta['gui2_url']
            },
            'ldap': {
                'enabled': self._ldap_login['enabled'],
                'default_domain': self._ldap_login['default_domain']
            },
            'saml': {
                'enabled': self._saml_login['enabled'],
                'idp_name': self._saml_login['idp_name']
            },
            'standard': {
                'disable_remember_me': self._system_settings['timeout_settings']['disable_remember_me']
            }
        })

    @gui_route_logged_in('login', methods=['GET'], enforce_permissions=False)
    def get_current_user(self):
        """
        Get current user or login
        :return:
        """
        user = self.get_session.get('user')
        if user is None:
            return return_error('Not logged in', 401)
        if 'pic_name' not in user:
            user['pic_name'] = self.DEFAULT_AVATAR_PIC
        user = dict(user)
        log_metric(logger, SystemMetric.LOGIN_MARKER, 0)
        user_name = user.get('user_name')
        source = user.get('source')
        if not self.is_axonius_user():
            self.send_external_info_log(f'UI Login with user: {user_name} of source {source}')
        if self._system_settings.get('timeout_settings') and self._system_settings.get('timeout_settings').get(
                'enabled'):
            user['timeout'] = self._system_settings.get('timeout_settings').get('timeout') \
                if not (os.environ.get('HOT') == 'true' or self.get_session.permanent) else 0
        return jsonify(beautify_user_entry(user)), 200

    @gui_route_logged_in('login', methods=['POST'], enforce_session=False,
                         limiter_key_func=get_remote_address, shared_limit_scope=LIMITER_SCOPE)
    def login(self):
        """
        do login
        :return:
        """
        log_in_data = self.get_request_data_as_object()
        if log_in_data is None:
            return return_error('No login data provided', 400)
        user_name = log_in_data.get('user_name')
        password = log_in_data.get('password')
        remember_me = log_in_data.get('remember_me', False)
        if not isinstance(remember_me, bool):
            return return_error('Illegal input', 400)
        if self._system_settings.get('timeout_settings') and self._system_settings.get('timeout_settings').get(
                'disable_remember_me'):
            remember_me = False
        user_from_db = self._users_collection.find_one(filter_archived({
            'user_name': user_name,
            'source': 'internal'  # this means that the user must be a local user and not one from an external service
        }))
        if user_from_db is None:
            logger.info(f'Unknown user {user_name} tried logging in')
            self.send_external_info_log(f'Unknown user {user_name} tried logging in')
            self._log_activity_login_failure(user_name)
            return return_error('Wrong user name or password', 401)

        if not bcrypt.verify(password, user_from_db['password']):
            self.send_external_info_log(f'User {user_name} tried logging in with wrong password')
            logger.info(f'User {user_name} tried logging in with wrong password')
            self._log_activity_login_failure(user_name)
            return return_error('Wrong user name or password', 401)
        role = self._roles_collection.find_one({'_id': user_from_db.get('role_id')})
        if request and request.referrer and 'localhost' not in request.referrer \
                and '127.0.0.1' not in request.referrer \
                and 'diag-l.axonius.com' not in request.referrer \
                and 'insider.axonius.lan' not in request.referrer \
                and not is_axonius_role(role):
            self.system_collection.replace_one({'type': 'server'},
                                               {'type': 'server', 'server_name': parse_url(request.referrer).host},
                                               upsert=True)

        self.__perform_login_with_user(user_from_db, remember_me)
        self._update_user_last_login(user_from_db)
        response = Response('')
        self._add_expiration_timeout_cookie(response)
        return response

    def _log_activity_login_failure(self, user_name):
        if request and request.referrer and ('localhost' in request.referrer or '127.0.0.1' in request.referrer
                                             or 'diag-l.axonius.com' in request.referrer):
            return

        self.log_activity_default(AuditCategory.UserSession.value,
                                  AuditAction.Failure.value,
                                  {'user_name': user_name},
                                  AuditType.Info)

    def _log_activity_login(self):
        self.log_activity_user(AuditCategory.UserSession, AuditAction.Login, {
            'status': 'successful'
        })

    def _update_user_last_login(self, user):
        user_id = user.get('_id')
        self._users_collection.find_one_and_update({
            '_id': ObjectId(user_id)
        }, {
            '$set': {'last_login': datetime.now()}
        })

    def __perform_login_with_user(self, user, remember_me=False):
        """
        Given a user, mark the current session as associated with it
        """
        user = dict(user)
        role_id = user.get('role_id')
        role_from_db = self._roles_collection.find_one({'_id': role_id})
        if not has_customer_login_happened() and not is_axonius_role(role_from_db):
            logger.info('First customer login occurred.')
            LOGGED_IN_MARKER_PATH.touch()
        logger.info(f'permission: {role_from_db["name"]}')
        user['permissions'] = deserialize_db_permissions(role_from_db['permissions'])
        user['role_name'] = role_from_db['name']
        user[PREDEFINED_FIELD] = role_from_db.get(PREDEFINED_FIELD)
        user[IS_AXONIUS_ROLE] = role_from_db.get(IS_AXONIUS_ROLE)
        self.get_session['user'] = user
        session['csrf-token'] = random_string(CSRF_TOKEN_LENGTH)
        self.get_session.permanent = remember_me
        self._log_activity_login()

    def __exteranl_login_successful(self, source: str,
                                    username: str,
                                    first_name: str = None,
                                    last_name: str = None,
                                    email: str = None,
                                    picname: str = None,
                                    remember_me: bool = False):
        """
        Our system supports external login systems, such as LDAP, and Okta.
        To generically support such systems with our permission model we must normalize the login mechanism.
        Once the code that handles the login with the external source finishes it must call this method
        to finalize the login.
        :param source: the name of the service that made the connection, i.e. 'LDAP'
        :param username: the username from the service, could also be an email
        :param first_name: the first name of the user (optional)
        :param last_name: the last name of the user (optional)
        :param email: the email of the user (optional)
        :param picname: the URL of the avatar of the user (optional)
        :param remember_me: whether or not to remember the session after the browser has been closed
        :return: None
        """
        db_connection = self._get_db_connection()
        config_collection = db_connection[GUI_PLUGIN_NAME][CONFIGURABLE_CONFIGS_COLLECTION]
        config_name = f'{source}_login_settings'
        config = config_collection.find_one({'config_name': f'GuiService'}, {f'config.{config_name}': 1})['config']
        default_role_id = None
        if config and config.get(config_name):
            default_role_id = config.get(config_name).get('default_role_id')
        if not default_role_id:
            restricted_role = self._roles_collection.find_one({'name': PREDEFINED_ROLE_RESTRICTED})
            default_role_id = restricted_role.get('_id')
        user = self._create_user_if_doesnt_exist(
            username,
            first_name,
            last_name,
            email=email,
            picname=picname,
            source=source,
            role_id=default_role_id
        )
        self.__perform_login_with_user(user, remember_me)

    @gui_route_logged_in('okta-redirect', enforce_session=False)
    def okta_redirect(self):
        okta_settings = self._okta
        if not okta_settings['enabled']:
            return return_error('Okta login is disabled', 400)
        oidc = try_connecting_using_okta(okta_settings)
        if oidc is not None:
            self.get_session['oidc_data'] = oidc
            # Notice! If you change the first parameter, then our CURRENT customers will have their
            # users re-created next time they log in. This is bad! If you change this, please change
            # the upgrade script as well.
            self.__exteranl_login_successful(
                'okta',  # Look at the comment above
                oidc.claims['email'],
                oidc.claims.get('given_name', ''),
                oidc.claims.get('family_name', ''),
                oidc.claims['email']
            )

        redirect_response = redirect('/', code=302)
        self._add_expiration_timeout_cookie(redirect_response)
        return redirect_response

    @staticmethod
    def __get_dc(ldap_login):
        """
        Try to connect to all DCs in ldap_login. Return the first successful one.
        Raises RESTException if all dcs failed to connect.
        Note: Automatically figures out port for test_reachability based on ldap_login['use_ssl']
        Uses port 389 if unencrypted, 636 otherwise.
        :param ldap_login: ldap login config dict
        :return: tuple(str dc_address, SSLState use_ssl)
        """
        dc_address_raw = ldap_login['dc_address']
        dc_address = None
        addresses = dc_address_raw.split(',')
        ssl_state = SSLState[ldap_login['use_ssl']]
        use_ssl = ssl_state != SSLState.Unencrypted
        port = 636 if use_ssl else 389
        for addr in addresses:
            dc_addr = addr.strip()
            can_conn = RESTConnection.test_reachability(dc_addr, port)
            if not can_conn:
                logger.warning(f'Failed to connect to DC at {dc_addr} with port {port}. '
                               f'Trying next one.')
            else:
                dc_address = dc_addr
                break
        if dc_address is None:
            raise RESTException(f'Connection to all DCs failed.')
        logger.debug(f'Using DC {dc_address}')
        return dc_address, ssl_state

    @gui_route_logged_in('login/ldap', methods=['POST'], enforce_session=False)
    def ldap_login(self):
        try:
            log_in_data = self.get_request_data_as_object()
            if log_in_data is None:
                return return_error('No login data provided', 400)
            user_name = log_in_data.get('user_name')
            password = log_in_data.get('password')
            domain = log_in_data.get('domain')
            ldap_login = self._ldap_login
            if not ldap_login['enabled']:
                return return_error('LDAP login is disabled', 400)

            def _log_return_error(message, login_user=None):
                if login_user:
                    self._log_activity_login_failure(login_user)
                return return_error(message)

            try:
                dc_address, use_ssl = self.__get_dc(ldap_login)
                conn = LdapConnection(dc_address, f'{domain}\\{user_name}', password,
                                      use_ssl=use_ssl,
                                      ca_file_data=self._grab_file_contents(
                                          ldap_login['private_key']) if ldap_login['private_key'] else None,
                                      cert_file=self._grab_file_contents(
                                          ldap_login['cert_file']) if ldap_login['cert_file'] else None,
                                      private_key=self._grab_file_contents(
                                          ldap_login['ca_file']) if ldap_login['ca_file'] else None)
            except RESTException:
                logger.exception(f'Failed to connect to any of the following DCs: {ldap_login.get("dc_address")}')
                return _log_return_error('Failed logging into AD: Connection to DC failed.')
            except LdapException:
                logger.exception('Failed login')
                return _log_return_error('Failed logging into AD', user_name)
            except Exception:
                logger.exception('Unexpected exception')
                return _log_return_error('Failed logging into AD')

            result = conn.get_user(user_name)
            if not result:
                return _log_return_error('Failed login', user_name)
            user, groups, groups_dn = result

            needed_group = ldap_login['group_cn']
            use_group_dn = ldap_login.get('use_group_dn') or False
            groups_prefix = [group.split('.')[0] for group in groups]
            if needed_group:
                if not use_group_dn:
                    if needed_group.split('.')[0] not in groups_prefix:
                        return _log_return_error(f'The provided user is not in the group {needed_group}')
                else:
                    if needed_group not in groups_dn:
                        return _log_return_error(f'The provided user is not in the group {needed_group}')
            image = None
            try:
                thumbnail_photo = user.get('thumbnailPhoto') or \
                    user.get('exchangePhoto') or \
                    user.get('jpegPhoto') or \
                    user.get('photo') or \
                    user.get('thumbnailLogo')
                if thumbnail_photo is not None:
                    if isinstance(thumbnail_photo, list):
                        thumbnail_photo = thumbnail_photo[0]  # I think this can happen from some reason..
                    image = bytes_image_to_base64(thumbnail_photo)
            except Exception:
                logger.exception(f'Exception while setting thumbnailPhoto for user {user_name}')

            # Notice! If you change the first parameter, then our CURRENT customers will have their
            # users re-created next time they log in. This is bad! If you change this, please change
            # the upgrade script as well.
            self.__exteranl_login_successful('ldap',  # look at the comment above
                                             user.get('displayName') or user_name,
                                             user.get('givenName') or '',
                                             user.get('sn') or '',
                                             '',
                                             image or self.DEFAULT_AVATAR_PIC)
            response = Response('')
            self._add_expiration_timeout_cookie(response)
            return response
        except ldap3.core.exceptions.LDAPException:
            return return_error('LDAP verification has failed, please try again')
        except Exception:
            logger.exception('LDAP Verification error')
            return return_error('An error has occurred while verifying your account')

    def __get_flask_request_for_saml(self, req):
        axonius_external_url = str(self._saml_login.get('axonius_external_url') or '').strip()
        if axonius_external_url:
            # do not parse the original host port and scheme, parse the input we got
            self_url = RESTConnection.build_url(axonius_external_url).strip('/')
        else:
            self_url = RESTConnection.build_url(req.url).strip('/')

        url_data = parse_url(self_url)
        req_object = {
            'https': 'on' if url_data.scheme == 'https' else 'off',
            'http_host': url_data.host,
            'server_port': url_data.port,
            'script_name': req.path,
            'get_data': req.args.copy(),
            'post_data': req.form.copy()
        }

        return self_url, req_object

    def __get_saml_auth_object(self, req, settings, parse_idp):
        # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
        self_url, req_object = self.__get_flask_request_for_saml(req)

        with open(self.saml_settings_file_path, 'rt') as f:
            saml_settings = json.loads(f.read())

        # configure service provider (us) settings
        saml_settings['sp']['entityId'] = f'{self_url}/api/login/saml/metadata/'
        saml_settings['sp']['assertionConsumerService']['url'] = f'{self_url}/api/login/saml/?acs'
        saml_settings['sp']['singleLogoutService']['url'] = f'{self_url}/api/logout/'

        # configure authentication context class
        # Note: If not set, requestedAuthnContext defaults to SAML library implicit default (AC_PASSWORD_PROTECTED)
        if (settings.get('configure_authncc') or {}).get('dont_send_authncc'):
            saml_settings.setdefault('security', {})['requestedAuthnContext'] = False

        # Now for the identity provider path.
        # At this point we must use the metadata file we have been provided in the settings, or use
        # the raw settings we have been provided.
        if parse_idp:
            # sometimes, the idp is not important (like when we are returning the metadata.
            if settings.get('metadata_url'):
                idp_settings = settings.get('idp_data_from_metadata')
                if not idp_settings:
                    raise ValueError('Metadata URL is invalid')

                if 'idp' not in idp_settings:
                    raise ValueError(f'Metadata XML does not contain "idp", please set the SAML config manually')

                saml_settings['idp'] = idp_settings['idp']
            else:
                try:
                    certificate = self._grab_file_contents(settings['certificate']).decode('utf-8').strip().splitlines()
                    if 'BEGIN CERTIFICATE' in certificate[0].upper():
                        # we must remove the header and footer
                        certificate = certificate[1:-1]

                    certificate = ''.join(certificate)

                    saml_settings['idp']['entityId'] = settings['entity_id']
                    saml_settings['idp']['singleSignOnService']['url'] = settings['sso_url']
                    saml_settings['idp']['x509cert'] = certificate

                except Exception:
                    logger.exception(f'Invalid SAML Settings: {saml_settings}')
                    raise ValueError(f'Invalid SAML settings, please check them!')

        try:
            auth = OneLogin_Saml2_Auth(req_object, saml_settings)
            return auth
        except Exception:
            logger.exception(f'Failed to create Saml2_Auth object, saml_settings: {saml_settings}')
            raise

    @gui_route_logged_in('login/saml/metadata/', methods=['GET', 'POST'], enforce_session=False)
    def saml_login_metadata(self):
        saml_settings = self._saml_login
        # Metadata can always exist, no need to check if SAML has been activated.

        auth = self.__get_saml_auth_object(request, saml_settings, False)
        settings = auth.get_settings()
        metadata = settings.get_sp_metadata()
        errors = settings.validate_metadata(metadata)

        if len(errors) == 0:
            resp = make_response(metadata, 200)
            resp.headers['Content-Type'] = 'text/xml'
            resp.headers['Content-Disposition'] = 'attachment; filename=axonius_saml_metadata.xml'
            return resp
        else:
            return return_error(', '.join(errors))

    @gui_route_logged_in('login/saml/', methods=['GET', 'POST'], enforce_session=False)
    def saml_login(self):
        self_url, req = self.__get_flask_request_for_saml(request)
        saml_settings = self._saml_login

        if not saml_settings['enabled']:
            return return_error('SAML-Based login is disabled', 400)

        auth = self.__get_saml_auth_object(request, saml_settings, True)

        if 'acs' in request.args:
            auth.process_response()
            errors = auth.get_errors()
            if len(errors) == 0:
                self_url_beginning = self_url

                if 'RelayState' in request.form and not request.form['RelayState'].startswith(self_url_beginning):
                    return redirect(auth.redirect_to(request.form['RelayState']))

                attributes = auth.get_attributes()
                name_id = auth.get_nameid() or \
                    attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name')

                given_name = attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname')
                surname = attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname')
                email = attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress')
                picture = None

                if not name_id:
                    logger.info(f'SAML Login failure, attributes are {attributes}')
                    self._log_activity_login_failure(str(email) if email else str(name_id))
                    raise ValueError(f'Error! SAML identity provider did not respond with attribute "name"')

                # Some of these attributes can come back as a list. If that is the case we just make things look nicer
                if isinstance(name_id, list) and len(name_id) == 1:
                    name_id = name_id[0]
                if isinstance(given_name, list) and len(given_name) == 1:
                    given_name = given_name[0]
                if isinstance(surname, list) and len(surname) == 1:
                    surname = surname[0]
                if isinstance(email, list) and len(email) == 1:
                    email = email[0]

                # Notice! If you change the first parameter, then our CURRENT customers will have their
                # users re-created next time they log in. This is bad! If you change this, please change
                # the upgrade script as well.
                self.__exteranl_login_successful('saml',  # look at the comment above
                                                 name_id,
                                                 given_name or name_id,
                                                 surname or '',
                                                 email,
                                                 picture or self.DEFAULT_AVATAR_PIC)

                logger.info(f'SAML Login success with name id {name_id}')
                redirect_response = redirect('/', code=302)
                self._add_expiration_timeout_cookie(redirect_response)
                return redirect_response
            else:
                return return_error(', '.join(errors) + f' - Last error reason: {auth.get_last_error_reason()}')

        else:
            redirect_response = redirect(auth.login())
            self._add_expiration_timeout_cookie(redirect_response)
            return redirect_response

    @staticmethod
    def _add_expiration_timeout_cookie(response):
        response.set_cookie('session_expiration', 'session_expiration')

    @gui_route_logged_in('logout', methods=['GET'], enforce_permissions=False)
    def logout(self):
        """
        Clears session, logs out
        :return:
        """
        user = self.get_session['user']
        username = user.get('user_name')
        source = user.get('source')
        first_name = user.get('first_name')
        logger.info(f'User {username}, {source}, {first_name} has logged out')
        self.log_activity_user(AuditCategory.UserSession, AuditAction.Logout)
        self.get_session['user'] = None
        self.get_session['csrf-token'] = None
        self.get_session.clear()
        return redirect('/', code=302)
