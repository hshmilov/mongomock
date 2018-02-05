import ctypes
import json
from contextlib import contextmanager
from retrying import retry

import axonius.adapter_exceptions
import eset_consts


class EsetClient(object):

    def __init__(self, lock, library, logger, host, username, password, port=22):
        self.client = library
        self.logger = logger
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.lock = lock
        self.connect()

    def _parse_simple_response_response(self, response, type_of_response='Era.ServerApi.SimpleResponse'):
        parsed_response = json.loads(response)
        return parsed_response.get(type_of_response, {}).get('result', False)

    def _send_message_to_server(self, session, message):
        response = session.SendMessage(message)
        retval = bytes(ctypes.c_char_p(response).value)

        session.FreeResponse(response)

        return retval

    @contextmanager
    def _get_session(self):
        with self.lock:
            try:
                # Starting request
                assert self._parse_simple_response_response(
                    self._send_message_to_server(self.client, eset_consts.START_REQUEST))

                # Setting host and port
                self._send_message_to_server(self.client,
                                             eset_consts.CONNECT.format(host=self.host, port=self.port).encode('utf-8'))

                # Verifying connection to server.
                assert self._parse_simple_response_response(
                    self._send_message_to_server(self.client, eset_consts.VERIFY_CONNECTION))

                # Authenticating.
                self._send_message_to_server(self.client, eset_consts.LOGIN.format(
                    username=self.username, password=self.password).encode('utf-8'))

                yield self.client
            except Exception:
                self.logger.exception("Failed opening a session.")
                raise axonius.adapter_exceptions.ClientConnectionException("Failed opening a session.")
            finally:
                self._send_message_to_server(self.client, eset_consts.CLOSE_CONNECTION)

                self._send_message_to_server(self.client, eset_consts.END_REQUEST)

    def connect(self):
        try:
            with self._get_session() as session:
                # Verifying login
                assert self._parse_simple_response_response(
                    self._send_message_to_server(session, eset_consts.LOGIN_CHECK),
                    type_of_response='Era.ServerApi.IsConnectionAliveResponse')
        except Exception:
            self.logger.exception("Failed connecting to eset")
            raise axonius.adapter_exceptions.ClientConnectionException("Failed to connect to eset.")

    def _get_report(self):
        """
        Generates a csv report from a pre-created report templates.
        :return: Mostly parsed devices.
        """

        def _parse_report_to_csv(response):
            return json.loads(response).get('Era.ServerApi.ReportCSVResponse', {}).get('reportCSV', '').split('\n')

        # Getting the raw data in the session first (to release the lock faster).
        # Getting all the data at once so no progress is logged
        with self._get_session() as session:
            # Get the basic data (IP, Hostname, OS, Last connected) raw
            most_data_raw = self._send_message_to_server(session, eset_consts.GENERATE_REPORT_FROM_TEMPLATE.format(
                report_template=eset_consts.COMMON_DATA_TEMPLATE).encode('utf-8'))

            # Getting the MAC address data raw.
            mac_data_raw = self._send_message_to_server(session, eset_consts.GENERATE_REPORT_FROM_TEMPLATE.format(
                report_template=eset_consts.MAC_ADDRESS_TEMPLATE).encode('utf-8'))

        # Parsing the raw basic data to csv.
        csv = _parse_report_to_csv(most_data_raw)

        # Holding the devices in a dict for o(1) when adding the mac address.
        devices = {}
        fields = csv.pop(0).split(',')
        for current_device in csv:
            new_device = {k: v for k, v in zip(fields, current_device.split(','))}
            devices[new_device['Computer name']] = new_device

        # Parsing and matching the Mac address data.
        csv = _parse_report_to_csv(mac_data_raw)
        fields = csv.pop(0).split(',')
        for current_device in csv:
            new_device = {k: v for k, v in zip(fields, current_device.split(','))}
            devices[new_device['Computer name']].update(new_device)

        return devices.values()

    def get_all_devices(self):
        return self._get_report()
