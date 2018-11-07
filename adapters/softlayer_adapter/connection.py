import functools
import logging
from concurrent.futures import wait, ThreadPoolExecutor, ALL_COMPLETED


logger = logging.getLogger(f'axonius.{__name__}')
from urllib3.util.url import parse_url
import SoftLayer
from softlayer_adapter.exceptions import SoftlayerConnectionError, SoftlayerRequestException


class SoftlayerConnection(object):
    def __init__(self, username: str, api_key: str, endpoint_url: str, proxy: str, verify: bool,
                 num_of_simultaneous_devices: int):
        """ Initializes a connection to SoftLayer using its rest API

        :param obj logger: Logger object of the system
        :param str domain: domain address for SoftLayer
        """
        self.client = SoftLayer.create_client_from_env(username=username, api_key=api_key, endpoint_url=endpoint_url,
                                                       proxy=proxy, verify=verify)
        self.num_of_simultaneous_devices = num_of_simultaneous_devices

    def connect(self):
        """ Connects to the service """
        try:
            self.client['Account'].getVirtualGuests(mask="mask[id]", limit=1, offset=1)
        except Exception as err:
            message = f'Error connecting to softlayer: {err}'
            logger.exception(message)
            raise SoftlayerConnectionError(message)

    def __del__(self):
        self.logout()

    def logout(self):
        """ Logs out of the service"""
        self.close()

    def close(self):
        """ Closes the connection """
        # nothing to do here
        pass

    def get_devices(self):
        yield from self.threaded_get_devices('getVirtualGuests', SoftLayer.VSManager(self.client).get_instance)
        yield from self.threaded_get_devices('getHardware', SoftLayer.HardwareManager(self.client).get_hardware)

    def threaded_get_devices(self, get_instances_func, get_details_func):
        """ Returns a list of all agents

        :param str data: the body of the request
        :return: the response
        :rtype: dict
        """
        def get_virtual_device(get_details_func, device_id, device_number):
            try:
                device_details = get_details_func(device_id['id'])
                if device_number % self.print_modulo == 0:
                    self.print_modulo *= 10
                    logger.info(f"Got {device_number} devices.")
                client_list.append(device_details)
            except Exception:
                logger.exception(f'error retrieving details of device id {device_id}')
        chunk = 1000
        offset = 0
        while True:
            results = self.client['Account'].call(get_instances_func, mask="mask[id]", offset=offset, limit=chunk)
            # It looks like we ran out results
            if not results:
                break
            offset += chunk
            client_list = []
            self._run_in_thread_pool_per_device(results, functools.partial(get_virtual_device, get_details_func))
            for device in client_list:
                yield device
            if len(results) < chunk:
                break

    def _run_in_thread_pool_per_device(self, devices_iter, func):
        logger.info("Starting {0} worker threads.".format(self.num_of_simultaneous_devices))
        with ThreadPoolExecutor(max_workers=self.num_of_simultaneous_devices) as executor:
            try:
                device_counter = 0
                self.print_modulo = 10
                futures = []

                # Creating a future for all the device summaries to be executed by the executors.
                for device in devices_iter:
                    device_counter += 1
                    futures.append(executor.submit(
                        func, device, device_counter))

                wait(futures, timeout=60 * 10, return_when=ALL_COMPLETED)
            except Exception as err:
                logger.exception("An exception was raised while trying to get the data.")

        logger.info("Finished getting all device data.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.close()
