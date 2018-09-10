
import logging
from datetime import datetime

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.fields import Field
from axonius.utils.files import get_local_config_file
from axonius.utils.parsing import parse_date, figure_out_cloud
from divvycloud_adapter import consts
from divvycloud_adapter.connection import DivvyCloudConnection

logger = logging.getLogger(f'axonius.{__name__}')


POWER_STATE_MAP = {
    'terminated': DeviceRunningState.TurnedOff,
    'poweredOff': DeviceRunningState.TurnedOff,
    'stopped': DeviceRunningState.TurnedOff,
    'poweredOn': DeviceRunningState.TurnedOn,
    'running': DeviceRunningState.TurnedOn,
    'pending': DeviceRunningState.TurnedOff,
    'shutting-down': DeviceRunningState.ShuttingDown,
    'stopping': DeviceRunningState.ShuttingDown,
    'suspended': DeviceRunningState.Suspended
}


class DivvycloudAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        divvycloud_instance_type = Field(str, "Instance Type")
        divvycloud_tenancy = Field(str, "Tenancy")
        divvycloud_launch_time = Field(datetime, "Launch Time")
        divvycloud_availability_zone = Field(str, "Availability Zone")
        divvycloud_region = Field(str, "Region")
        divvycloud_cloud_nickname = Field(str, "Cloud Nickname")
        divvycloud_organization_service_id = Field(int, "Organization Service ID")
        divvycloud_resource_id = Field(str, "Resource ID")
        divvycloud_network_resource_id = Field(str, "Network Resource ID")
        divvycloud_image_id = Field(str, "Image ID")
        divvycloud_key_name = Field(str, "Key name")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        return '{1}@{0}'.format(client_config['domain'], client_config['username'])

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get('domain', ''),
                                                client_config.get('port') or consts.DEFAULT_PORT,
                                                ssl='https://' in client_config.get('domain', ''))

    def _connect_client(self, client_config):
        try:
            # The default url scheme in RESTConnection is https, but the default scheme in DivvyCloud is http.
            # so we add a prefix if its not already there.

            domain = client_config['domain']
            if "://" not in client_config['domain']:
                domain = f"http://{domain}"

            connection = DivvyCloudConnection(domain=domain,
                                              verify_ssl=client_config.get("verify_ssl"),
                                              port=client_config.get('port', consts.DEFAULT_PORT),
                                              username=client_config['username'],
                                              password=client_config['password'],
                                              headers={
                                                  'Content-Type': 'application/json;charset=UTF-8',
                                                  'Accept': 'application/json'}
                                              )
            with connection:
                pass  # check that the connection credentials are valid
            return connection
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, session):
        try:
            session.connect()
            yield from session.get_device_list()
        finally:
            session.close()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "domain",
                    "title": "DivvyCloud Domain",
                    "type": "string"
                },
                {
                    "name": "port",
                    "title": "Port (Default is 8001)",
                    "type": "integer",
                    "format": "port"
                },
                {
                    "name": "username",
                    "title": "Username",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string",
                    "format": "password"
                },
                {
                    "name": "verify_ssl",
                    "title": "Verify SSL",
                    "type": "bool"
                }
            ],
            "required": [
                "domain",
                "username",
                "password",
                "verify_ssl"
            ],
            "type": "array"
        }

    def create_device(self, raw_device_data):
        device = self._new_device_adapter()

        device.id = raw_device_data["instance_id"]
        device.cloud_id = raw_device_data["instance_id"]
        device.figure_os(raw_device_data.get("platform", ""))

        device.divvycloud_instance_type = raw_device_data.get("instance_type")
        device.divvycloud_tenancy = raw_device_data.get("tenancy")
        device.divvycloud_launch_time = parse_date(raw_device_data.get("launch_time"))

        device.power_state = POWER_STATE_MAP.get(raw_device_data.get('state', DeviceRunningState.Unknown))
        try:
            ips = []
            private_ip_address = raw_device_data.get("private_ip_address")
            if private_ip_address:
                ips.append(private_ip_address)
            public_ip_address = raw_device_data.get("public_ip_address")
            if public_ip_address:
                ips.append(public_ip_address)

            device.add_nic(ips=ips)
        except Exception:
            logger.exception(f"Problem parsing ip addresses")

        device.divvycloud_image_id = raw_device_data.get("image_id")
        device.divvycloud_key_name = raw_device_data.get("key_name")
        device.divvycloud_network_resource_id = raw_device_data.get("network_resource_id")

        # More info resides in the "common" dict
        raw_common = raw_device_data.get("common") or {}

        device.name = raw_common.get("resource_name")
        device.divvycloud_availability_zone = raw_common.get("availability_zone")
        device.divvycloud_region = raw_common.get("region")
        device.divvycloud_cloud_nickname = raw_common.get("account")
        device.divvycloud_resource_id = raw_common.get("resource_id")

        device.cloud_provider = figure_out_cloud(raw_common.get("cloud"))

        try:
            for key, value in raw_common.get("tags", {}).items():
                device.add_key_value_tag(key, value)
        except Exception:
            logger.exception(f'Problem adding key value tags: {raw_common.get("tags")}')

        try:
            device.divvycloud_organization_service_id = raw_common.get("organization_service_id")
        except Exception:
            logger.exception(
                f'Problem parsing divvycloud organization service id: {raw_common.get("organization_service_id")}')

        device.last_seen = parse_date(raw_common.get("modified_timestamp"))

        device.set_raw(raw_device_data)
        return device

    def _parse_raw_data(self, raw_data):
        try:
            for raw_device_data in iter(raw_data):
                try:
                    device = self.create_device(raw_device_data)
                    yield device
                except Exception:
                    logger.exception(f'Got an exception for raw_device_data: {raw_device_data}')
        except Exception:
            logger.exception(f'Got an exception in _parse_raw_data')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
