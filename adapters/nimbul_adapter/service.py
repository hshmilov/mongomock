from collections import defaultdict
import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter
from axonius.utils.files import get_local_config_file
from axonius.utils.datetime import parse_date
from nimbul_adapter.client_id import get_client_id
from nimbul_adapter.connection import NimbulConnection

logger = logging.getLogger(f'axonius.{__name__}')


class NimbulAdapter(AdapterBase):
    # pylint: disable=R0902
    class MyDeviceAdapter(DeviceAdapter):
        app_code = Field(str, 'Application Code')
        app_description = Field(str, 'Application Description')
        app_email = Field(str, 'Application Email')
        app_permission = Field(str, 'Application Permission')
        app_slack = Field(str, 'Application Slack Channel')
        app_team = Field(str, 'Application Team')
        app_department = Field(str, 'Application Department')
        app_security_type = Field(str, 'Application Security Type')

        cluster_name = Field(str, 'Cluster Name')
        environment_name = Field(str, 'Environment Name')
        subnet_name = Field(str, 'Subnet Name')
        vpc_name = Field(str, 'VPC Name')
        volume_snapshot_frequencies = Field(str, 'Volume Snapshot Frequencies')
        cloud_state = Field(str, 'Cloud State')

        updated_at = Field(datetime.datetime, 'Updated At')
        launch_date = Field(datetime.datetime, 'Launch Date')
        last_scanned = Field(datetime.datetime, 'Last Scanned')
        created_at = Field(datetime.datetime, 'Created At')
        patch_level = Field(str, 'Patch Level')

        project_name = Field(str, 'Project Name')
        project_application_name = Field(str, 'Project Application Name')
        project_application_email = Field(str, 'Project Appliaction Email')

    class MyUserAdapter(UserAdapter):
        nimbul_source = Field(str, 'Nimbul Source')
        user_instances = ListField(str, 'User Instances')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    def _test_reachability(self, client_config):
        return RESTConnection.test_reachability('https://nimbul-api.nyt.net')

    def _connect_client(self, client_config):
        try:
            connection = NimbulConnection(domain='https://nimbul-api.nyt.net',
                                          url_base_prefix='api/v1/',
                                          apikey=client_config['token'])
            with connection:
                pass
            return connection
        except Exception as e:
            # pylint: disable=W1202
            logger.error('Failed to connect to client {0}'.format(
                self._get_client_id(client_config)))
            raise ClientConnectionException(str(e))

    def _query_devices_by_client(self, client_name, client_data):
        self._users_to_devices_dict = defaultdict(list)
        with client_data:
            self._app_dict = client_data.get_apps()
            self._project_dict = client_data.get_project()
            yield from client_data.get_device_list()

    def _query_users_by_client(self, key, data):
        with data:
            yield from data.get_user_list()

    def _clients_schema(self):
        return {
            'items': [
                {
                    'name': 'token',
                    'title': 'API Token',
                    'type': 'string',
                    'format': 'password'
                }
            ],
            'required': [
                'token'
            ],
            'type': 'array'
        }

    def __add_project_data(self, device, project_name, cloud_id):
        try:
            if not project_name:
                return
            project_data = self._project_dict.get(project_name)
            if not project_data:
                return
            device.project_application_name = project_data.get('application_name')
            project_application_email = project_data.get('application_email')
            if project_application_email:
                device.project_application_email = project_application_email
            if project_application_email and cloud_id:
                if not self._users_to_devices_dict[project_application_email]:
                    self._users_to_devices_dict[project_application_email] = []
                if cloud_id not in self._users_to_devices_dict[project_application_email]:
                    self._users_to_devices_dict[project_application_email].append(cloud_id)

        except Exception:
            logger.exception(f'Problem adding project specfic data')

    def __add_app_data(self, device, device_raw, cloud_id=None):
        try:
            app_id = device_raw.get('app_id')
            if not app_id:
                return
            app_data = self._app_dict.get(app_id)
            if not app_data:
                return
            device.app_code = app_data.get('code')
            app_email = app_data.get('email')
            if app_email and cloud_id:
                device.app_email = app_email
                if not self._users_to_devices_dict[app_email]:
                    self._users_to_devices_dict[app_email] = []
                if cloud_id not in self._users_to_devices_dict[app_email]:
                    self._users_to_devices_dict[app_email].append(cloud_id)
            device.app_description = app_data.get('description')
            device.app_permission = app_data.get('permission')
            device.app_slack = app_data.get('slack_channel')
            device.app_team = app_data.get('team')
            device.app_department = app_data.get('department')
            device.app_security_type = app_data.get('security_type')

        except Exception:
            logger.exception(f'Problem adding app data to {device_raw}')

    def _create_device_instance(self, device_raw):
        device = self._new_device_adapter()
        if not device_raw.get('instance_id'):
            logger.warning(f'Bad device with no ID {device_raw}')
            return None
        device.id = str(device_raw.get('instance_id'))
        cloud_id = device_raw.get('cloud_id')
        device.cloud_id = cloud_id
        image_cloud_id = device_raw.get('image_cloud_id')
        device.volume_snapshot_frequencies = device_raw.get('volume_snapshot_frequencies')
        if image_cloud_id and image_cloud_id.startswith('ami-'):
            device.cloud_provider = 'AWS'
        device.hostname = device_raw.get('hostname')
        vpc_name = device_raw.get('vpc_name')
        if vpc_name:
            if vpc_name.startswith('GCP:'):
                device.cloud_provider = 'GCP'
            device.vpc_name = vpc_name
        device.app_code = device_raw.get('app_code')
        device.app_description = device_raw.get('app_description')
        device.app_email = device_raw.get('app_email')
        device.cluster_name = device_raw.get('cluster_name')
        device.environment_name = device_raw.get('environment_name')
        device.subnet_name = device_raw.get('subnet_name')

        try:
            subnet = device_raw.get('subnet')
            if subnet and isinstance(subnet, str):
                subnets = [subnet]
            else:
                subnets = None
            private_ip = device_raw.get('private_ip')
            if private_ip and isinstance(private_ip, str):
                private_ip = [private_ip]
            if private_ip:
                device.add_nic(None, private_ip, subnets=subnets)

            public_ip = device_raw.get('public_ip')
            if public_ip and isinstance(public_ip, str):
                public_ip = [public_ip]
            if public_ip:
                device.add_public_ip(public_ip)
        except Exception:
            logger.exception(f'Problem getting ip for {device_raw}')
        self.__add_app_data(device, device_raw, cloud_id)
        device.set_raw(device_raw)
        return device

    def _create_device_unmanaged(self, device_raw):
        device = self._new_device_adapter()
        if not device_raw.get('id'):
            logger.warning(f'Bad device with no ID {device_raw}')
            return None
        device.id = str(device_raw.get('id')) + str(device_raw.get('cloud_uid'))
        device.name = device_raw.get('cloud_uid')
        cloud_id = device_raw.get('cloud_uid')
        device.cloud_id = cloud_id
        device.cloud_state = device_raw.get('cloud_state')
        image_cloud_id = device_raw.get('image_cloud_id')
        if image_cloud_id and image_cloud_id.startswith('ami-'):
            device.cloud_provider = 'AWS'
        try:
            private_ip = device_raw.get('private_ip_address')
            if private_ip and isinstance(private_ip, str):
                private_ip = [private_ip]
            if private_ip:
                device.add_nic(None, private_ip)

            public_ip = device_raw.get('public_ip_address')
            if public_ip and isinstance(public_ip, str):
                public_ip = [public_ip]
            if public_ip:
                device.add_public_ip(public_ip)
        except Exception:
            logger.exception(f'Problem getting ip for {device_raw}')
        try:
            device.updated_at = parse_date(device_raw.get('updated_at'))
            device.launch_date = parse_date(device_raw.get('launch_date'))
            device.last_scanned = parse_date(device_raw.get('last_scanned'))
            device.created_at = parse_date(device_raw.get('created_at'))
            device.patch_level = device_raw.get('patch_level')
        except Exception:
            logger.exception(f'Problem at parse date {device_raw}')
        self.__add_app_data(device, device_raw, cloud_id)
        try:
            full_name = device_raw.get('name')
            if full_name and 'googleapis' in full_name and '/projects/' in full_name:
                project_name = full_name.split('/')[full_name.split('/').index('projects') + 1]
                device.project_name = project_name
                self.__add_project_data(device, project_name, cloud_id)
        except Exception:
            logger.exception(f'Problem adding project name')

        device.set_raw(device_raw)
        return device

    def _create_user_user(self, user_raw):
        user = self._new_user_adapter()
        mail = user_raw.get('email')
        if not mail:
            return None
        user.id = mail
        user.mail = mail
        user.nimbul_source = user_raw.get('source')
        try:
            if self._users_to_devices_dict.get(mail):
                user.user_instances = self._users_to_devices_dict.get(mail)
        except Exception:
            logger.exception(f'Problem adding instances to {user_raw}')
        user.set_raw(user_raw)
        return user

    # pylint: disable=W0221
    def _parse_users_raw_data(self, raw_users):
        for user_type, user_raw in iter(raw_users):
            try:
                user = None
                if user_type == 'user':
                    user = self._create_user_user(user_raw)
                if user:
                    yield user
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {user_raw}')

    def _parse_raw_data(self, devices_raw_data):
        for device_type, device_raw in iter(devices_raw_data):
            try:
                device = None
                if device_type == 'unmanaged':
                    device = self._create_device_unmanaged(device_raw)
                elif device_type == 'instance':
                    device = self._create_device_instance(device_raw)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {device_raw}')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]
