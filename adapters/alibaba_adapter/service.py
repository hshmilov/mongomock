import json
import logging

# The below APIs come from Alibaba Cloud open SDK for Python
# The documentation can be accessed here: https://github.com/aliyun/aliyun-openapi-python-sdk
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field
from axonius.utils.files import get_local_config_file

logger = logging.getLogger(f'axonius.{__name__}')


ALIBABA_ACCESS_KEY_ID = 'access_key_id'
ALIBABA_ACCESS_SECRET_KEY = 'access_key_secret'
REGION_ID = 'region_id'
MAX_PAGES_TO_PREVENT_INFINITE_LOOP = 10000


class AlibabaAdapter(AdapterBase):

    def _parse_correlation_results(self, correlation_cmd_result, os_type):
        pass

    class MyDeviceAdapter(DeviceAdapter):
        alibaba_region = Field(str, 'Alibaba Cloud ECS Region')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return client_config[ALIBABA_ACCESS_KEY_ID]

    def _connect_client(self, client_config):
        try:
            alibaba_client = AcsClient(client_config[ALIBABA_ACCESS_KEY_ID],
                                       client_config[ALIBABA_ACCESS_SECRET_KEY], client_config[REGION_ID])

            # The only way to see if the connection works is to try a request
            request = DescribeInstancesRequest.DescribeInstancesRequest()
            _ = alibaba_client.do_action_with_exception(request)

            return alibaba_client
        except Exception as e:
            logger.error(f'Failed to connect to client {format(self._get_client_id(client_config))}')
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        """
        The way the Alibaba Cloud API works, you must first make a generic DescribeInstanceseRequest that is
        independent of client_data and just specifies the kind of request and how many instances to display.
        Below in the while loop, the client_data is actually used to make the request. This must be done multiple
        times since each request returns a "page" of a specific number of instances, and therefore multiple requests
        must be executed to return all the "pages" with all the instances.
        """

        request = DescribeInstancesRequest.DescribeInstancesRequest()
        request.set_PageSize(100)

        has_next_page = True
        page_number = 1

        # Alibaba ECS devices are separated onto different pages of varying size, so we iterate through
        # each page and for each page, iterate through the list of instances on that page
        while has_next_page is True and page_number < MAX_PAGES_TO_PREVENT_INFINITE_LOOP:
            request.set_PageNumber(page_number)
            # do_action_with_exception is an Alibaba Cloud method that actually executes the kind of request
            # that is given as a parameter for the specified client data. In this case, it is executing a
            # DescribeInstancesRequest that lists all Alibaba Cloud ECS instances.
            response = client_data.do_action_with_exception(request)
            raw_data = json.loads(response)
            instances = raw_data.get('Instances').get('Instance')
            # Instances will always exist for an empty page, but its list of instances will be empty
            if not instances:
                has_next_page = False
            else:
                raw_data = raw_data.get('Instances').get('Instance')
                for raw_device in raw_data:
                    yield raw_device
                page_number += 1

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': REGION_ID,
                    'title': 'Region ID',
                    'type': 'string'
                },
                {
                    'name': ALIBABA_ACCESS_KEY_ID,
                    'title': 'Alibaba Access Key ID',
                    'type': 'string'
                },
                {
                    'name': ALIBABA_ACCESS_SECRET_KEY,
                    'title': 'Alibaba Access Key Secret',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                REGION_ID,
                ALIBABA_ACCESS_KEY_ID,
                ALIBABA_ACCESS_SECRET_KEY
            ],
            'type': 'array'
        }

    def create_device(self, raw_device_data):
        device = self._new_device_adapter()
        device.id = raw_device_data['InstanceId']
        try:
            device.name = raw_device_data.get('InstanceName')
            device.figure_os(raw_device_data.get('OSName'))
            device.alibaba_region = raw_device_data.get('RegionId')
            device.total_physical_memory = raw_device_data.get('Memory')
            device.hostname = raw_device_data.get('HostName')
        except Exception as e:
            logger.error(f'Failed to get basic device information for device {device.id}. Error: {e}')
        try:
            ips = (raw_device_data.get('PublicIpAddress') or {}).get('IpAddress', [])
            if not isinstance(ips, list):
                ips = [ips]
            device.add_nic(ips=ips)
        except Exception as e:
            logger.error(f'Failed to get public ips for device {device.id}')
        try:
            device_nics = raw_device_data.get('NetworkInterfaces').get('NetworkInterface')
            for device_nic in device_nics:
                try:
                    device.add_nic(mac=device_nic.get('MacAddress'), ips=[device_nic.get(
                        'PrimaryIpAddress')], name=device_nic.get('NetworkInterfaceId'))
                except Exception:
                    logger.error(f'Failed to add nic')
        except Exception as e:
            logger.error(f'Failed to get nics for device {device.id}')

        device.set_raw(raw_device_data)
        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]

    def _test_reachability(self, client_config):
        # We must actually try the request and see that it fails with the correct exception.
        # we are using different credentials just to see if we get an 'invalid access key id' that indicates
        # the server indeed responded
        try:
            # We are assuming that if we have connectivity to one region than we have to all of them
            alibaba_client = AcsClient('a', 'a', 'us-west-1')
            request = DescribeInstancesRequest.DescribeInstancesRequest()
            _ = alibaba_client.do_action_with_exception(request)
            # We should not get to this point, since we should have an error happening before
            logger.error(f'Error - test reachability worked even though it had to raise an exception')
            return False
        except ServerException as e:
            if 'HTTP Status: 404 Error:InvalidAccessKeyId' in str(e):
                # This is the error we expect to have when we have connectivity
                return True
            logger.exception(f'Server Exception Error - Unknown Error')
            return False
        except Exception:
            logger.exception('Error when testing reachability to Alibaba')
            return False
