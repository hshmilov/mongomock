import json
import logging
import datetime

from google.oauth2 import service_account
from googleapiclient import discovery
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState, Provider
from axonius.smart_json_class import SmartJsonClass

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.fields import Field, ListField
from axonius.utils.files import get_local_config_file
from axonius.utils.json_encoders import IgnoreErrorJSONEncoder
from axonius.utils.parsing import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


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


class GceTag(SmartJsonClass):
    gce_key = Field(str, 'GCE Key')
    gce_value = Field(str, 'GCE Value')


class GceAdapter(AdapterBase):
    class MyDeviceAdapter(DeviceAdapter):
        project_id = Field(str, 'Project ID')
        public_ips = ListField(str, 'Public IPs')
        image = Field(str, 'Device image')
        size = Field(str, 'Google Device Size')
        creation_time_stamp = Field(datetime.datetime, 'Creation Time Stamp')
        cluster_name = Field(str, 'GCE Cluster Name')
        cluster_uid = Field(str, 'GCE Cluster Unique ID')
        cluster_location = Field(str, 'GCE Cluster Location')
        gce_tags = ListField(GceTag, 'GCE Tags')
        service_accounts = ListField(str, 'Service Accounts')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
        return auth_file['client_id'] + '_' + auth_file['project_id']

    def _test_reachability(self, client_config):
        raise NotImplementedError()

    def _connect_client(self, client_config):
        try:
            auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))

            return auth_file
        except Exception as e:
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        auth_json = client_data
        try:
            credentials = service_account.Credentials.\
                from_service_account_info(auth_json,
                                          scopes=['https://www.googleapis.com/auth/cloudplatformprojects.readonly'])
            service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
            request = service.projects().list()
            while request is not None:
                response = request.execute()
                for project in response['projects']:
                    try:
                        for device_raw in get_driver(Provider.GCE)(auth_json['client_email'], auth_json['private_key'], project=project.get('projectId')).list_nodes():
                            yield device_raw, project.get('projectId')
                    except Exception:
                        logger.exception(f'Problem with project {project}')
                request = service.projects().list_next(previous_request=request, previous_response=response)
        except Exception:
            for device_raw in get_driver(Provider.GCE)(auth_json['client_email'], auth_json['private_key'], project=auth_json['project_id']).list_nodes():
                yield device_raw, auth_json['project_id']

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'keypair_file',
                    'title': 'JSON Key pair for the service account',
                    'description': 'The binary contents of the JSON keypair file',
                    'type': 'file',
                },
            ],
            'required': [
                'keypair_file'
            ],
            'type': 'array'
        }

    def create_device(self, raw_device_data, project_id):
        device = self._new_device_adapter()
        device.id = raw_device_data.id
        device.cloud_provider = 'GCP'
        device.cloud_id = device.id
        device.project_id = project_id
        try:
            device.power_state = POWER_STATE_MAP.get(raw_device_data.state,
                                                     DeviceRunningState.Unknown)
        except Exception:
            logger.exception(f'Coudn\'t get power state for {str(raw_device_data)}')
        try:
            device.figure_os(raw_device_data.image)
        except Exception:
            logger.exception(f'Coudn\'t get os for {str(raw_device_data)}')
        try:
            device.name = raw_device_data.name
        except Exception:
            logger.exception(f'Coudn\'t get name for {str(raw_device_data)}')
        try:
            device.add_nic(ips=raw_device_data.private_ips)
        except Exception:
            logger.exception(f'Coudn\'t get ips for {str(raw_device_data)}')
        try:
            public_ips = raw_device_data.public_ips
            if public_ips:
                for ip in public_ips:
                    if ip:
                        device.public_ips.append(ip)
        except Exception:
            logger.exception(f'Problem getting public IP for {str(raw_device_data)}')
        try:
            device.image = raw_device_data.image
        except Exception:
            logger.exception(f'Problem getting image for {str(raw_device_data)}')
        try:
            device.size = raw_device_data.size
        except Exception:
            logger.exception(f'Problem getting data size for {str(raw_device_data)}')
        try:
            device.creation_time_stamp = parse_date(raw_device_data.extra.get('creationTimestamp'))
        except Exception:
            logger.exception(f'Problem getting creation time for {str(raw_device_data)}')
        try:
            for item in (raw_device_data.extra.get('metadata').get('items') or []):
                if item.get('key') == 'cluster-name':
                    device.cluster_name = item.get('value')
                elif item.get('key') == 'cluster-uid':
                    device.cluster_uid = item.get('value')
                elif item.get('key') == 'cluster-location':
                    device.cluster_location = item.get('value')
                else:
                    try:
                        gce_key = item.get('key')
                        gce_value = item.get('value')
                        device.gce_tags.append(GceTag(gce_key=gce_key, gce_value=gce_value))
                    except Exception:
                        logger.exception(f'Problemg getting extra tags for {raw_device_data}')
        except Exception:
            logger.exception(f'Problem getting cluster info for {str(raw_device_data)}')
        try:
            device.service_accounts = []
            service_accounts_raw = raw_device_data.extra.get('serviceAccounts')
            if isinstance(service_accounts_raw, list) and service_accounts_raw:
                for service_account_raw in service_accounts_raw:
                    try:
                        if service_account_raw.get('email'):
                            device.service_accounts.append(service_account_raw.get('email'))
                    except Exception:
                        logger.exception(f'Problem with service account {service_account_raw}')
        except Exception:
            logger.exception(f'Problem adding Service Accounts')
        try:
            # some fields might not be basic types
            # by using IgnoreErrorJSONEncoder with JSON encode we verify that this
            # will pass a JSON encode later by mongo
            device.set_raw(json.loads(json.dumps(raw_device_data.__dict__, cls=IgnoreErrorJSONEncoder)))
        except Exception:
            logger.exception(f'Can\'t set raw for {str(device.id)}')
        return device

    def _parse_raw_data(self, devices_raw_data):
        for raw_device_data, project_id in iter(devices_raw_data):
            try:
                device = self.create_device(raw_device_data, project_id)
                yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {raw_device_data}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]
