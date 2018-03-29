from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter, Field
from axonius.utils.files import get_local_config_file
from openstack_adapter.client import OpenStackClient
from urllib3.util.url import parse_url
from axonius.adapter_exceptions import ClientConnectionException


class OpenstackAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        status = Field(str, "Status")
        image_name = Field(str, "Image name")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        # TODO: is there a better place to set default values for client_config?
        client_config.setdefault('domain', 'default')

        return '{}/{}'.format(parse_url(client_config['auth_url']).hostname, client_config['project'])

    def _connect_client(self, client_config):
        try:
            client = OpenStackClient(self.logger, **client_config)
            client.connect()
            return client
        except ClientConnectionException as err:
            self.logger.error('Failed to connect to client {0} using config: {1}'.format(
                self._get_client_id(client_config), client_config))
            raise

    def _query_devices_by_client(self, client_name, session):
        for device in session.get_devices():
            flavor = session.get_flavor(device)
            image = session.get_image(device)
            yield (device, flavor, image)

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "auth_url",
                    "title": "auth_url",
                    "type": "string",
                    "description": "Authentication URL - from dashboard/project/api_access/ -> View Credentials"
                },
                {
                    "name": "username",
                    "title": "User Name",
                    "type": "string"
                },
                {
                    "name": "password",
                    "title": "Password",
                    "type": "string"
                },
                {
                    "name": "project",
                    "title": "Project",
                    "type": "string",
                    "description": "Project Name"
                },
                {
                    "name": "domain",
                    "title": "Domain",
                    "type": "string",
                    "description": 'Default domain name (default: "Default")'
                },

            ],
            "required": [
                "auth_url",
                "username",
                "password",
                "project",
            ],
            "type": "array"
        }

    def create_device(self, raw_device_data):
        raw_device, flavor, image = raw_device_data
        # add basic info
        device = self._new_device_adapter()
        device.id = raw_device['id']
        device.name = raw_device['name']
        device.status = raw_device['status']

        # if the device has image
        if image:
            device.image_name = image['name']

        # if the machine has flavor
        if flavor:
            device.total_physical_memory = flavor['ram'] / 1024
            device.number_of_processes = flavor['vcpus']

        # iterate the nics and add them
        for mac, ip_address in OpenStackClient.get_nics(raw_device).items():
            device.add_nic(mac, ip_address, logger=self.logger)

        device.set_raw(
            {"device": raw_device, "flavor": flavor, "image": image})

        return device

    def _parse_raw_data(self, raw_data):
        for raw_device_data in iter(raw_data):
            try:
                device = self.create_device(raw_device_data)
                yield device
            except Exception:
                self.logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
