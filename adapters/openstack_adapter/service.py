# pylint: disable=import-error
import logging
import datetime
logger = logging.getLogger(f'axonius.{__name__}')
from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter, Field
from axonius.utils.files import get_local_config_file
from openstack_adapter.client import OpenStackClient
from axonius.utils.datetime import parse_date
from urllib3.util.url import parse_url
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection


class OpenstackAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        status = Field(str, "Status")
        image_name = Field(str, "Image name")
        role = Field(str, 'Role')
        uai = Field(str, 'UAI')
        alternate_contacts = Field(str, 'Alternate Contacts')
        app = Field(str, 'Application')
        cloud_location_zone = Field(str, 'Cloud Location Zone')
        criticality = Field(str, 'Criticality')
        env = Field(str, 'Environment')
        realrolename = Field(str, 'Real Role Name')
        region = Field(str, 'Region')
        scalr_version = Field(str, 'Scalr Version')
        vm_state = Field(str, 'VM State')
        image_create_time = Field(datetime.datetime, 'Image Creation Time')
        image_update_time = Field(datetime.datetime, 'Image Update Time')
        image_uai = Field(str, 'Image UAI')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        # TODO: is there a better place to set default values for client_config?
        client_config.setdefault('domain', 'default')

        return '{}/{}'.format(parse_url(client_config['auth_url']).hostname, client_config['project'])

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability(client_config.get("auth_url"), ssl=False)

    def _connect_client(self, client_config):
        try:
            client = OpenStackClient(**client_config)
            client.connect()
            client.disconnect()
            return client
        except ClientConnectionException as err:
            logger.exception('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise

    def _query_devices_by_client(self, client_name, session):
        session.connect()
        try:
            for device in session.get_devices():
                try:
                    flavor = None
                    try:
                        flavor = session.get_flavor(device)
                    except Exception:
                        logger.debug(f'Problem with flavour', exc_info=True)
                    image = None
                    try:
                        image = session.get_image(device)
                    except Exception:
                        logger.debug(f'Problem with image', exc_info=True)
                    yield (device, flavor, image)
                except Exception:
                    logger.exception(f'Problem with device')
        finally:
            session.disconnect()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "auth_url",
                    "title": "Authentication URL",
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
                    "type": "string",
                    "format": "password"
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
        device.id = raw_device['id'] + '_' + (raw_device.get('name') or '')
        device.name = raw_device.get('name')
        metadata = raw_device.get('metadata')
        if not isinstance(metadata, dict):
            metadata = {}
        device.status = raw_device.get('status')
        device.role = metadata.get('Role') or metadata.get('role')
        device.uai = metadata.get('UAI') or metadata.get('uai')
        device.alternate_contacts = metadata.get('alternate_contacts')
        device.app = metadata.get('app')
        device.cloud_location_zone = metadata.get('cloud_location_zone')
        device.criticality = metadata.get('criticality')
        device.env = metadata.get('env')
        device.email = metadata.get('owner_email')
        device.realrolename = metadata.get('realrolename')
        device.region = metadata.get('region')
        device.scalr_version = metadata.get('scalr_version')
        device.vm_state = raw_device.get('vm_state')

        # if the device has image
        if image:
            try:
                device.image_name = image.get('name')
                device.image_create_time = parse_date(image.get('created_at'))
                device.image_update_time = parse_date(image.get('updated_at'))
                device.image_uai = (image.get('metadata') or {}).get('uai')
            except Exception:
                logger.exception(f'Problem with image')

        # if the machine has flavor
        if flavor:
            try:
                try:
                    device.total_physical_memory = flavor['ram'] / 1024
                except Exception:
                    pass
                try:
                    device.number_of_processes = flavor['vcpus']
                except Exception:
                    pass
                if flavor.get('disk'):
                    device.add_hd(total_size=flavor.get('disk'))
            except Exception:
                logger.exception(f'Problem with flavor')

        # iterate the nics and add them
        try:
            for mac, ip_address in OpenStackClient.get_nics(raw_device).items():
                try:
                    device.add_nic(mac, ip_address)
                except Exception:
                    logger.exception(f'Problem getting mac ip')
        except Exception:
            logger.exception(f'Problem getting nics')

        device.set_raw(
            {"device": raw_device, "flavor": flavor, "image": image})

        return device

    def _parse_raw_data(self, raw_data):
        for raw_device_data in iter(raw_data):
            try:
                device = self.create_device(raw_device_data)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
