"""
fortigate
"""
# pylint: disable=import-error
import logging
from contextlib import contextmanager
from json.decoder import JSONDecodeError
import requests
import uritools
from bs4 import BeautifulSoup

from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.clients.rest.consts import get_default_timeout
from fortigate_adapter.consts import (DEFAULT_DHCP_LEASE_TIME,
                                      DEFAULT_FORTIGATE_PORT)

logger = logging.getLogger(f'axonius.{__name__}')

# pylint: disable=C0111, I0021


class FortigateClient():
    def __init__(self, host, username, password, verify_ssl=False, port=DEFAULT_FORTIGATE_PORT,
                 vdom=None, dhcp_lease_time=DEFAULT_DHCP_LEASE_TIME, is_fortimanager=None):
        if port is None:
            port = DEFAULT_FORTIGATE_PORT
        if dhcp_lease_time is None:
            dhcp_lease_time = DEFAULT_DHCP_LEASE_TIME

        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.verify_ssl = verify_ssl
        if not vdom:
            vdom = None
        self.vdom = vdom
        self.dhcp_lease_time = dhcp_lease_time  # In Seconds
        self.test_connection()

    def test_connection(self):
        try:
            with self._get_session():
                pass

        except ClientConnectionException:
            logger.exception('Failed connecting to fortigate')
            raise
        except Exception:
            logger.exception('Failed connecting to fortigate')
            raise ClientConnectionException('Failed to connect to fortigate.')

    def _make_request(self, session, method, resource, payload=None):
        url = uritools.urijoin(RESTConnection.build_url(domain=self.host, port=self.port), resource)
        response = session.request(method, url,
                                   data=payload, verify=self.verify_ssl, params={'vdom': self.vdom},
                                   timeout=get_default_timeout())
        response.raise_for_status()
        try:
            return response.json()
        except JSONDecodeError:
            # All cases that return 200 status code (That would not raise an exception on raise_for_status())
            # Return json except for login and logout in-which we don't care about the content.
            return response.content

    @contextmanager
    def _get_session(self):
        with requests.session() as session:

            # Login and save the auth header.
            response = self._make_request(session,
                                          'post',
                                          'logincheck',
                                          {'username': self.username, 'secretkey': self.password})

            soup = BeautifulSoup(response)
            if soup.title and soup.title.text == 'Login Failed':
                raise ClientConnectionException(soup.body.text)

            for cookie in session.cookies:
                if cookie.name == 'ccsrftoken':
                    csrftoken = cookie.value[1:-1]
                    session.headers.update({'X-CSRFTOKEN': csrftoken})
                    break
            else:
                raise ClientConnectionException('Unable to find ccsrftoken')

            if csrftoken == '0%260':
                raise ClientConnectionException('Got Invalid ccsrftoken, (invalid password?)')
            # Return the authenticated session.
            yield session

            # Logout.
            self._make_request(session, 'get', 'logout')

    def get_all_devices(self, fortios_name):
        with self._get_session() as session:
            raw_devices = self._make_request(session, 'get', 'api/v2/monitor/system/dhcp/')
            raw_devices.update({'dhcp_lease_time': self.dhcp_lease_time})
            for current_interface in (raw_devices.get('results') or []):
                try:
                    for raw_device in current_interface.get('list',
                                                            [current_interface]):  # If current interface does'nt hold
                        raw_device['fortios_name'] = fortios_name
                        yield raw_device, 'fortios_device'
                except Exception:
                    # pylint: disable=W1203
                    logger.exception(f'Problem with interface {str(current_interface)}')
            try:
                managed_aps = self._make_request(session, 'get', 'api/v2/monitor/wifi/managed_ap/')
                ipsec_vpns = self._make_request(session, 'get', 'api/v2/monitor/vpn/ipsec')
                wifi_clients = self._make_request(session, 'get', 'api/v2/monitor/wifi/client')
                for raw_ap_device in (managed_aps.get('results') or []):
                    try:
                        raw_ap_device['fortios_name'] = fortios_name
                        yield raw_ap_device, 'fortigate_access_point'
                    except Exception:
                        logger.exception('Problem with access point')
                for vpn_device in (ipsec_vpns.get('results') or []):
                    try:
                        vpn_device['fortios_name'] = fortios_name
                        yield vpn_device, 'fortigate_vpn'
                    except Exception:
                        logger.exception('Problem with VPN')
                for wifi_client in (wifi_clients.get('resources') or []):
                    try:
                        wifi_client['fortios_name'] = fortios_name
                        yield wifi_client, 'fortigate_wifi_client'
                    except Exception:
                        logger.exception('Problem with wifi client')
            except Exception:
                logger.exception(f'Problem getting extended fortigate data')
