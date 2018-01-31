import concurrent.futures
import time
from contextlib import contextmanager
import ssl
import dateutil.parser


import nexpose.nexpose as nexpose

from axonius.adapter_base import AdapterBase
from axonius.device import Device

PASSWORD = 'password'
USER = 'username'
NEXPOSE_HOST = 'host'
NEXPOSE_PORT = 'port'
VERIFY_SSL = 'verify_ssl'


class NexposeAdapter(AdapterBase):
    """
    Connects axonius to Rapid7's nexpose.
    """

    class MyDevice(Device):
        pass

    def __init__(self, **kwargs):
        """Class initialization.

        Check AdapterBase documentation for additional params and exception details.

        """

        # Initialize the base plugin (will initialize http server)
        super().__init__(**kwargs)
        self.num_of_simultaneous_requests = int(self.config["DEFAULT"]["num_of_simultaneous_requests"])

    def _wait_for_status(self, session, expected_status, message):
        self.logger.info(message)
        while True:
            status = session.GetSecurityConsoleStatus()
            self.logger.info("Current status:{0}".format(status))
            if status == expected_status:
                break
            time.sleep(5)

    @contextmanager
    def _get_session(self, should_verify_ssl, client_data):
        """A context manager for session object, to be used only with."""
        if not should_verify_ssl:
            # Handle target environment that doesn't support HTTPS verification
            _create_unverified_https_context = ssl._create_unverified_context
            ssl._create_default_https_context = _create_unverified_https_context

        session = nexpose.NexposeSession.Create(**client_data)
        self._wait_for_status(session, nexpose.NexposeStatus.NORMAL_MODE, "Waiting for the console to be ready:")
        self.logger.info("The Security Console is ready...")
        session.Open()
        try:
            yield session
        except Exception as err:
            self.logger.exception('An exception occurred while in session')
        finally:
            session.Close()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": NEXPOSE_HOST,
                    "title": "Host Name",
                    "type": "string"
                },
                {
                    "name": NEXPOSE_PORT,
                    "title": "Port",
                    "type": "number"
                },
                {
                    "name": USER,
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": PASSWORD,
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {  # if false, it will allow for invalid SSL certificates (but still uses HTTPS)
                    "name": VERIFY_SSL,
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                USER,
                PASSWORD,
                NEXPOSE_PORT,
                NEXPOSE_HOST,
            ],
            "type": "array"
        }

    def _parse_raw_data(self, devices_raw_data):
        # We do not use data with no timestamp.
        no_timestamp_count = 0
        for device_raw in devices_raw_data:
            try:
                last_seen = device_raw.get('last_scan_date')
                if last_seen is None:
                    # No data on the last timestamp of the device. Not inserting this device.
                    no_timestamp_count += 1
                    continue

                # Parsing the timestamp and setting the tz to None.
                last_seen = dateutil.parser.parse(last_seen)
            except Exception as err:
                self.logger.exception("An Exception was raised while getting and parsing the last_seen field.")
                continue

            device_raw['tags'] = str(device_raw.get('tags', ''))

            device = self._new_device()
            device.figure_os(device_raw.get('os_name'))
            device.last_seen = last_seen
            device.id = str(device_raw['id'])
            device.add_nic(device_raw.get('mac_address', ''), device_raw.get('addresses', []), self.logger)
            device.hostname = device_raw['host_names'][0] if len(device_raw.get('host_names', [])) > 0 else ''
            device.scanner = True
            device.set_raw(device_raw)
            yield device

        if no_timestamp_count != 0:
            self.logger.warning(f"Got {no_timestamp_count} with no timestamp while parsing data")

    def _query_devices_by_client(self, client_name, client_data):
        should_verify_ssl = client_data.pop(VERIFY_SSL, False)
        with self._get_session(should_verify_ssl, client_data) as session:
            devices = self.get_all_devices(session)
        return devices

    def _parse_nexpose_asset_details_to_dict(self, asset_details):
        """
        Goes over the attibutes of nexpose's AssetDetails and creates a viable dict from them.
        :param asset_details: The AssetDetails object to parse to dict.
        :return: a dict.
        """
        details = dict()
        # The reason for getting rid of 'unique_identifiers' is that it's a specialized class that I didn't see
        # a reason to parse because there isn't new data here but just data we already got.
        for current_detail in \
                [attribute for attribute in dir(asset_details) if not attribute.startswith('__') and
                 not callable(getattr(asset_details,
                                      attribute)) and
                 attribute != 'unique_identifiers']:
            details[current_detail] = getattr(asset_details, current_detail)
        return details

    def get_all_devices(self, session):
        """
        Pushing all the asset summaries to a queue and requesting details simultaneously
        from predefined number of workers
        :param session: The NexposeSession to use.
        :return: A list of all devices (dicts).
        """
        def get_details_worker(device_summary, device_number):
            device_details = {}
            try:
                device_details = session.GetAssetDetails(device_summary)
                device_details = self._parse_nexpose_asset_details_to_dict(device_details)
            except Exception as err:
                self.logger.exception("An exception occured while getting and parsing device details from nexpose.")

            # Writing progress to log every 100 devices.
            if device_number % 100 == 0:
                self.logger.info("Got {0} devices.".format(device_number))

            return device_details

        raw_detailed_devices = []

        self.logger.info("Starting {0} worker threads.".format(self.num_of_simultaneous_requests))
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_of_simultaneous_requests) as executor:
            device_counter = 0
            future_to_device = []
            # Creating a future for all the device summaries to be executed by the executors.
            for device_summary in session.GetAssetSummaries():
                device_counter += 1
                future_to_device.append(executor.submit(get_details_worker, device_summary, device_counter))

            self.logger.info("Getting data for {0} devices.".format(device_counter))

            for future in concurrent.futures.as_completed(future_to_device):
                try:
                    raw_detailed_devices.append(future.result())
                except Exception as err:
                    self.logger.exception("An exception was raised while trying to get a result.")

        self.logger.info("Finished getting all device data.")

        return raw_detailed_devices

    def _get_client_id(self, client_config):
        return client_config[NEXPOSE_HOST]

    def _connect_client(self, client_config):
        return client_config
