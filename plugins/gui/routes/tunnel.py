import base64
import gzip
import datetime
import json
import logging
from pathlib import Path
from smtplib import SMTPDataError

from flask import Response, request

from axonius.consts.core_consts import CORE_CONFIG_NAME
from axonius.consts.gui_consts import FeatureFlagsNames
from axonius.consts.plugin_consts import INSTANCE_CONTROL_PLUGIN_NAME, CORE_UNIQUE_NAME, \
    CONFIGURABLE_CONFIGS_COLLECTION, TUNNEL_SETTINGS, TUNNEL_EMAILS_RECIPIENTS, TUNNEL_PROXY_SETTINGS, \
    TUNNEL_PROXY_ADDR, TUNNEL_PROXY_PORT, TUNNEL_PROXY_USER, TUNNEL_PROXY_PASSW
from axonius.consts.system_consts import VPN_DATA_DIR_FROM_GUI
from axonius.logging.audit_helper import AuditCategory, AuditAction, AuditType
from axonius.plugin_base import return_error
from axonius.utils.permissions_helper import PermissionCategory
from gui.logic.routing_helper import gui_category_add_rules, gui_route_logged_in
from gui.logic.tunnel_config_builder import base_config
# pylint: disable=no-member,access-member-before-definition

logger = logging.getLogger(f'axonius.{__name__}')

DOCKER_PING_CMD = 'docker exec -i openvpn-service ping -c 4 {ip}'
DEFAULT_TUNNEL_CLIENT_IP = '192.167.255.2'
EXPECTED_RESULT = '4 packets transmitted, 4 packets received'


@gui_category_add_rules('tunnel', permission_category=PermissionCategory.Settings)
class Tunnel:
    ##################
    # Tunnel Service #
    ##################

    @gui_route_logged_in('get_status', methods=['GET'], enforce_trial=True)
    def check_tunnel_status(self, internal_use=True):
        """
        Check the tunnel status by pinging the tunnel server and making sure it response
        If the status has changed since last time (taken first time when gui container is up) it updates accordingly.
        :param internal_use: For internal use only (logging, sending emails, internal calls not related to user)
        :return: Response object with the text 'True' or 'False' that corresponds the tunnel status.
        """
        if not self.feature_flags_config().get(FeatureFlagsNames.EnableSaaS, False):
            return Response('Tunnel is not enabled on system')

        res = self._trigger_remote_plugin(
            INSTANCE_CONTROL_PLUGIN_NAME,
            job_name='execute_shell',
            data={'cmd': DOCKER_PING_CMD.format(ip=DEFAULT_TUNNEL_CLIENT_IP)},
            timeout=30,
            stop_on_timeout=True,
            priority=True
        )
        res.raise_for_status()
        res = res.text
        if internal_use:
            status = '4 packets transmitted, 4 packets received' in res
            if not status == self.tunnel_status and not status:
                self.log_activity(AuditCategory.Tunnel, AuditAction.Disconnected, activity_type=AuditType.Error)
                self.create_notification('Tunnel is disconnected')
                self.send_tunnel_status_update_email()
            elif not status == self.tunnel_status and status:
                self.log_activity(AuditCategory.Tunnel, AuditAction.Connected)
            self.tunnel_status = status
            return Response(str(status))

        return Response(str(EXPECTED_RESULT in res))

    def _tunnel_is_down(self):
        if self.tunnel_status:
            self.log_activity(AuditCategory.Tunnel, AuditAction.Disconnected, activity_type=AuditType.Error)
            self.create_notification('Tunnel is disconnected')
            self.send_tunnel_status_update_email()
            self.tunnel_status = False

    def _tunnel_is_up(self):
        if not self.tunnel_status:
            self.log_activity(AuditCategory.Tunnel, AuditAction.Connected)
            self.tunnel_status = True

    @gui_route_logged_in('download_agent', methods=['GET'], enforce_trial=True)
    # pylint: disable=no-self-use
    def generate_dockerfile_for_agent(self):
        """
        Generate a unique installer to the customer
        :return: A sh file (bash script) for installing the tunnel.
        """
        headers = {
            'Content-Disposition': f'attachment; filename=axonius_agent_launcher.sh',
            'Content-Type': 'text/plain'
        }
        if (Path(VPN_DATA_DIR_FROM_GUI) / 'user.ovpn').exists():
            payload = (Path(VPN_DATA_DIR_FROM_GUI) / 'user.ovpn').read_bytes()
        else:
            return return_error('User configuration file not exists')
        proxy_settings = self._get_tunnel_proxy_settings()
        return Response(
            base_config.format(payload=base64.b64encode(gzip.compress(payload, compresslevel=9)).decode('utf-8'),
                               proxy_enabled=proxy_settings['enabled'],
                               proxy_username=proxy_settings[TUNNEL_PROXY_USER],
                               proxy_password=proxy_settings[TUNNEL_PROXY_PASSW],
                               proxy_addr=proxy_settings[TUNNEL_PROXY_ADDR],
                               proxy_port=proxy_settings[TUNNEL_PROXY_PORT]),
            headers=headers)

    @gui_route_logged_in('emails_list', methods=['GET', 'POST'], enforce_trial=True)
    def emails_list(self):
        if request.method == 'GET':
            return Response(json.dumps(self._get_tunnel_email_recipients()))
        new_emails = request.get_json()
        if isinstance(new_emails, list):
            self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION, CORE_UNIQUE_NAME).update_one({
                'config_name': 'CoreService'
            }, {
                '$set': {
                    f'config.{TUNNEL_SETTINGS}.{TUNNEL_EMAILS_RECIPIENTS}': new_emails
                }
            })
            return Response(True)
        return return_error('Emails received not in list format')

    @gui_route_logged_in('proxy_settings', methods=['GET', 'POST'], enforce_trial=True)
    def proxy_settings(self):
        if request.method == 'GET':
            return Response(json.dumps(self._get_tunnel_proxy_settings()))

        try:
            post_data = request.get_json()
            if isinstance(post_data, dict):
                self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION, CORE_UNIQUE_NAME).update_one({
                    'config_name': 'CoreService'
                }, {
                    '$set': {
                        f'config.{TUNNEL_SETTINGS}.{TUNNEL_PROXY_SETTINGS}.enabled': post_data['enabled'],
                        f'config.{TUNNEL_SETTINGS}.{TUNNEL_PROXY_SETTINGS}.{TUNNEL_PROXY_ADDR}': post_data[
                            TUNNEL_PROXY_ADDR],
                        f'config.{TUNNEL_SETTINGS}.{TUNNEL_PROXY_SETTINGS}.{TUNNEL_PROXY_PORT}': post_data[
                            TUNNEL_PROXY_PORT],
                        f'config.{TUNNEL_SETTINGS}.{TUNNEL_PROXY_SETTINGS}.{TUNNEL_PROXY_USER}': post_data[
                            TUNNEL_PROXY_USER],
                        f'config.{TUNNEL_SETTINGS}.{TUNNEL_PROXY_SETTINGS}.{TUNNEL_PROXY_PASSW}': post_data[
                            TUNNEL_PROXY_PASSW]
                    }
                })
                self.log_activity_user(AuditCategory.PluginSettings, AuditAction.Post, {'config_name': 'Tunnel'})
                return Response(True)
            return return_error('Tunnel settings schema not as requested', 400)
        except Exception:
            logger.error(f'Problem in saving tunnel proxy settings', exc_info=True)
            return return_error('Problem in saving tunnel proxy settings', 400)

    def _get_tunnel_proxy_settings(self):
        core_config = self._get_collection(CONFIGURABLE_CONFIGS_COLLECTION, CORE_UNIQUE_NAME).find_one(
            {'config_name': 'CoreService'})['config']
        return core_config.get(TUNNEL_SETTINGS, {}).get(TUNNEL_PROXY_SETTINGS, None)

    def _get_tunnel_email_recipients(self):
        email_recipients = self._get_db_connection()[CORE_UNIQUE_NAME][CONFIGURABLE_CONFIGS_COLLECTION].find_one(
            {'config_name': CORE_CONFIG_NAME})['config'].get(TUNNEL_SETTINGS, None)
        if not email_recipients:
            return []
        return email_recipients.get(TUNNEL_EMAILS_RECIPIENTS, [])

    def send_tunnel_status_update_email(self):
        recipients = self._get_tunnel_email_recipients()
        if self.mail_sender and recipients:
            try:
                email = self.mail_sender.new_email('Axonius Tunnel is disconnected',
                                                   recipients)
                email.send(f'Axonius Tunnel is disconnected since'
                           f' {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC.\n<br>'
                           f'A connection with the Axonius Tunnel is required to fetch data from various adapters.'
                           f' For details, see <a href="https://docs.axonius.com/docs/installing-axonius-tunnel">'
                           f'Installing Axonius Tunnel</a>')

            except SMTPDataError:
                logger.error('Error while contacting SMTP Server', exc_info=True)
            except Exception:
                logger.error('Error in sending tunnel disconnected email', exc_info=True)
            else:
                return True
        return False
