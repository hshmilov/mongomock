import json
import logging

from axonius.utils.json_encoders import IgnoreErrorJSONEncoder

logger = logging.getLogger(f'axonius.{__name__}')

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.utils.files import get_local_config_file
from axonius.adapter_exceptions import ClientConnectionException
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.providers import get_driver
from axonius.fields import Field, ListField


POWER_STATE_MAP = {
    NodeState.STOPPED: DeviceRunningState.TurnedOff,
    NodeState.RUNNING: DeviceRunningState.TurnedOn,
    NodeState.SUSPENDED: DeviceRunningState.Suspended,
    NodeState.STOPPING: DeviceRunningState.ShuttingDown,
    NodeState.ERROR: DeviceRunningState.Error,
    NodeState.MIGRATING: DeviceRunningState.Migrating,
    NodeState.REBOOTING: DeviceRunningState.Rebooting,
    NodeState.STARTING: DeviceRunningState.StartingUp,
}


class GceAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        public_ips = ListField(str, "Public IPs")
        image = Field(str, "Device image")
        size = Field(str, "Google Device Size")
        creation_time_stamp = Field(str, "Creation Time Stamp")
        cluster_name = Field(str, "GCE Cluster Name")
        cluster_uid = Field(str, "GCE Cluster Unique ID")
        cluster_location = Field(str, "GCE Cluster Location")

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
        return auth_file['client_id']

    def _test_reachability(self, client_config):
        return True

    def _connect_client(self, client_config):
        try:
            auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))

            return get_driver(Provider.GCE)(auth_file['client_email'],
                                            auth_file['private_key'],
                                            project=auth_file['project_id'])
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, session):
        return session.list_nodes()

    def _clients_schema(self):
        return {
            "items": [
                {
                    "name": "keypair_file",
                    "title": "JSON Key pair for the service account",
                    "description": "The binary contents of the JSON keypair file",
                    "type": "file",
                },
            ],
            "required": [
                'keypair_file'
            ],
            "type": "array"
        }

    def create_device(self, raw_device_data):
        device = self._new_device_adapter()
        device.id = raw_device_data.id
        try:
            device.power_state = POWER_STATE_MAP.get(raw_device_data.state,
                                                     DeviceRunningState.Unknown)
        except Exception:
            logger.exception(f"Coudn't get power state for {str(raw_device_data)}")
        try:
            device.figure_os(raw_device_data.image)
        except Exception:
            logger.exception(f"Coudn't get os for {str(raw_device_data)}")
        try:
            device.name = raw_device_data.name
        except Exception:
            logger.exception(f"Coudn't get name for {str(raw_device_data)}")
        try:
            device.add_nic(ips=raw_device_data.private_ips)
        except Exception:
            logger.exception(f"Coudn't get ips for {str(raw_device_data)}")
        try:
            device.public_ips = list(raw_device_data.public_ips)
        except Exception:
            logger.exception(f"Problem getting public IP for {str(raw_device_data)}")
        try:
            device.image = raw_device_data.image
        except Exception:
            logger.exception(f"Problem getting image for {str(raw_device_data)}")
        try:
            device.size = raw_device_data.size
        except Exception:
            logger.exception(f"Problem getting data size for {str(raw_device_data)}")
        try:
            device.creation_time_stamp = raw_device_data.extra.get('creationTimestamp')
        except Exception:
            logger.exception(f"Problem getting creation time for {str(raw_device_data)}")
        try:
            for item in (raw_device_data.extra.get('metadata').get('items') or []):
                if item.get('key') == 'cluster-name':
                    device.cluster_name = item.get('value')
                elif item.get('key') == 'cluster-uid':
                    device.cluster_uid = item.get('value')
                elif item.get('key') == 'cluster-location':
                    device.cluster_location = item.get('value')
        except Exception:
            logger.exception(f"Problem getting cluster info for {str(raw_device_data)}")

        try:
            # some fields might not be basic types
            # by using IgnoreErrorJSONEncoder with JSON encode we verify that this
            # will pass a JSON encode later by mongo
            device.set_raw(json.loads(json.dumps(raw_device_data.__dict__, cls=IgnoreErrorJSONEncoder)))
        except Exception:
            logger.exception(f"Can't set raw for {str(device.id)}")
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
