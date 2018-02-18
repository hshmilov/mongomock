import requests
from contextlib import contextmanager
from json.decoder import JSONDecodeError

import axonius.adapter_exceptions
from fortigate_adapter.consts import DEFAULT_FORTIGATE_PORT, DEFAULT_DHCP_LEASE_TIME


class FortigateClient(object):

    def __init__(self, logger, host, username, password, verify_ssl=False, port=DEFAULT_FORTIGATE_PORT,
                 vdom=None, dhcp_lease_time=DEFAULT_DHCP_LEASE_TIME):
        if port is None:
            port = DEFAULT_FORTIGATE_PORT
        if dhcp_lease_time is None:
            dhcp_lease_time = DEFAULT_DHCP_LEASE_TIME
        self.logger = logger
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.verify_ssl = verify_ssl
        self.vdom = vdom
        self.dhcp_lease_time = dhcp_lease_time  # In Seconds
        self.test_connection()

    def test_connection(self):
        try:
            with self._get_session():
                pass

        except Exception as err:
            self.logger.exception("Failed connecting to fortigate")
            raise axonius.adapter_exceptions.ClientConnectionException("Failed to connect to fortigate.")

    def _make_request(self, session, method, resource, payload=None):
        response = getattr(session, method)(f'https://{self.host}:{self.port}/{resource}',
                                            data=payload, verify=self.verify_ssl, params={'vdom': self.vdom})
        response.raise_for_status()
        try:
            return response.json()
        except JSONDecodeError as err:
            # All cases that return 200 status code (That would not raise an exception on raise_for_status())
            # Return json except for login and logout in-which we don't care about the content.
            return response.content

    @contextmanager
    def _get_session(self):
        with requests.session() as session:

            # Login and save the auth header.
            self._make_request(session, 'post', 'logincheck', {'username': self.username, 'secretkey': self.password})

            for cookie in session.cookies:
                if cookie.name == 'ccsrftoken':
                    csrftoken = cookie.value[1:-1]
                    session.headers.update({'X-CSRFTOKEN': csrftoken})
                    break

            # Return the authenticated session.
            yield session

            # Logout.
            self._make_request(session, 'get', 'logout')

    def get_all_devices(self):
        with self._get_session() as session:
            raw_devices = self._make_request(session, 'get', 'api/v2/monitor/system/dhcp/')
            raw_devices.update({'dhcp_lease_time': self.dhcp_lease_time})
            return raw_devices
