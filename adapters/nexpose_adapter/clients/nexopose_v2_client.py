from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from retrying import retry
import ssl

from axonius.adapter_exceptions import ClientConnectionException, AdapterException
from nexpose.nexpose import NexposeSession
from nexpose.nexpose_status import NexposeStatus
from nexpose_adapter.clients.nexpose_base_client import NexposeClient


class NexposeV2Client(NexposeClient):

    @contextmanager
    def _get_session(self):
        """A context manager for session object, to be used only with."""
        @retry(stop_max_attempt_number=10, wait_fixed=5000, retry_on_result=lambda result: result is False)
        def _wait_for_status(session, expected_status):
            return session.GetSecurityConsoleStatus() == expected_status

        if not self.verify_ssl:
            # Handle target environment that doesn't support HTTPS verification
            ssl._create_default_https_context = ssl._create_unverified_context

        session = NexposeSession.Create(self.host, self.port, self.username, self.password)
        connected = _wait_for_status(session, NexposeStatus.NORMAL_MODE)
        if not connected:
            raise ClientConnectionException("Did not successfully create session with nexpose client.")
        session.Open()
        try:
            yield session
        except:
            raise AdapterException('An exception occurred while in session')
        finally:
            session.Close()

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

    def get_all_devices(self):
        """
        Pushing all the asset summaries to a queue and requesting details simultaneously
        from predefined number of workers
        :param session: The NexposeSession to use.
        :return: A list of all devices (dicts).
        """
        def get_details_worker(device_summary, device_number, session):
            device_details = {}
            try:
                device_details = session.GetAssetDetails(device_summary)
                device_details = self._parse_nexpose_asset_details_to_dict(device_details)
                device_details['API'] = '2'
            except Exception as err:
                self.logger.exception("An exception occured while getting and parsing device details from nexpose.")

            # Writing progress logs in a logarithm (10's then 100's then 1000's).
            # Because of lack of sum of devices.
            device_number_to_notify = 10 ** (len(str(device_number)) - 1)
            if device_number % device_number_to_notify == 0:
                self.logger.info("Got {0} devices.".format(device_number))

            return device_details

        raw_detailed_devices = []

        self.logger.info("Starting {0} worker threads.".format(self.num_of_simultaneous_devices))
        with ThreadPoolExecutor(max_workers=self.num_of_simultaneous_devices) as executor:
            try:
                with self._get_session() as session:
                    device_counter = 0
                    future_to_device = []

                    # Creating a future for all the device summaries to be executed by the executors.
                    for device_summary in session.GetAssetSummaries():
                        device_counter += 1
                        future_to_device.append(executor.submit(
                            get_details_worker, device_summary, device_counter, session))

                    self.logger.info("Getting data for {0} devices.".format(device_counter))

                    for future in as_completed(future_to_device):
                        try:
                            raw_detailed_devices.append(future.result())
                        except Exception as err:
                            self.logger.exception("An exception was raised while trying to get a result.")
            except Exception as err:
                self.logger.exception("An exception was raised while trying to get the data.")

        self.logger.info("Finished getting all device data.")

        return raw_detailed_devices

    def _does_api_exist(self):
        with self._get_session() as session:
            successfully_connected = isinstance(session, NexposeSession)
        return successfully_connected

    @staticmethod
    def parse_raw_device(device_raw, device_class, logger):
        # We do not use data with no timestamp.
        last_seen = device_raw.get('last_scan_date')
        last_seen = super(NexposeV2Client, NexposeV2Client).parse_raw_device_last_seen(last_seen)

        device_raw['tags'] = str(device_raw.get('tags', ''))

        device = device_class()
        device.figure_os(device_raw.get('os_name'))
        device.last_seen = last_seen
        device.id = str(device_raw['id'])
        device.add_nic(device_raw.get('mac_address', ''), device_raw.get('addresses', []), logger)
        device.hostname = device_raw['host_names'][0] if len(device_raw.get('host_names', [])) > 0 else ''
        risk_score = device_raw.get('riskScore')
        if risk_score is not None:
            try:
                device.risk_score = float(risk_score)
            except Exception as e:
                logger.exception("Cant get risk score")
        device.scanner = True
        device.set_raw(device_raw)
        return device
