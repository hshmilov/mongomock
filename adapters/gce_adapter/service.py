import datetime
import enum
import ipaddress
import json
import logging
from collections import defaultdict
from typing import Iterable, List, Tuple

from libcloud.compute.drivers.gce import GCEFirewall
from libcloud.compute.providers import get_driver
from libcloud.compute.types import NodeState, Provider

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection
from axonius.devices.device_adapter import DeviceAdapter, DeviceRunningState
from axonius.fields import Field, JsonArrayFormat, JsonStringFormat, ListField
from axonius.mixins.configurable import Configurable
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from axonius.utils.json_encoders import IgnoreErrorJSONEncoder
from axonius.utils.parsing import format_subnet
from gce_adapter.connection import GoogleCloudPlatformConnection
from gce_adapter.consts import SQL_INSTANCE_STATES, SQL_DB_VERSIONS, SQL_SUSP_REASONS, SQL_INSTANCE_TYPES, \
    SCC_FINDING_STATES

logger = logging.getLogger(f'axonius.{__name__}')

GCE_ENDPOINT_FOR_REACHABILITY_TEST = f'https://www.googleapis.com/discovery/v1/apis/compute/v1/rest'

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


class DeviceType(enum.Enum):
    COMPUTE = 1
    STORAGE = 2
    DATABASE = 3
    SCC_ASSET = 4


class GCPUserRolePerms(SmartJsonClass):
    name = Field(str, 'Name')
    title = Field(str, 'Title')
    descr = Field(str, 'Description')
    perms = ListField(str, 'Included Permissions')
    deleted = Field(bool, 'Deleted')


class GceTag(SmartJsonClass):
    gce_key = Field(str, 'GCE Key')
    gce_value = Field(str, 'GCE Value')


class GceFirewallRule(SmartJsonClass):
    type = Field(str, 'Allowed / Denied', enum=['Allowed', 'Denied'])
    protocol = Field(str, 'Protocol')
    ports = ListField(str, 'Ports')  # Ports can also be a range like 50-60 so it can't be int


class GceFirewall(SmartJsonClass):
    name = Field(str, 'Firewall Name')
    direction = Field(str, 'Direction', enum=['INGRESS', 'EGRESS'])
    priority = Field(int, 'Priority')
    match = ListField(str, 'Matched By')
    source_ranges = ListField(str, 'Source ranges', converter=format_subnet, json_format=JsonStringFormat.subnet)
    source_tags = ListField(str, 'Source tags')
    source_service_accounts = ListField(str, 'Source service accounts')
    destination_ranges = ListField(str, 'Destination ranges',
                                   converter=format_subnet, json_format=JsonStringFormat.subnet)
    target_ranges = ListField(str, 'Target ranges', converter=format_subnet, json_format=JsonStringFormat.subnet)
    target_tags = ListField(str, 'Target tags')
    target_service_accounts = ListField(str, 'Target service accounts')
    rules = ListField(GceFirewallRule, 'Rules')


class GCPBucketIamConf(SmartJsonClass):
    uniform_blaccess = Field(bool, 'Uniform Bucket Level Access')
    bucket_policy_only = Field(bool, 'Bucket Policy Only')


class GCPStorageObject(SmartJsonClass):
    content_type = Field(str, 'Content Type')
    name = Field(str, 'Object Name')
    etag = Field(str, 'Storage Object eTag')
    generation = Field(str, 'Generation')
    md5_hash = Field(str, 'MD5 Hash')
    modified = Field(datetime.datetime, 'Last Modified')
    crc32c = Field(str, 'CRC32 Checksum')
    metageneration = Field(str, 'Metageneration')
    media_url = Field(str, 'Media Link')
    size = Field(int, 'Size')
    created = Field(datetime.datetime, 'Created')
    id = Field(str, 'Storage Object ID')
    self_link = Field(str, 'API Self-Link')
    storage_class = Field(str, 'Storage Class')
    storage_class_updated = Field(datetime.datetime, 'Time Storage Class Updated')


class CloudSQLSettings(SmartJsonClass):
    ver = Field(str, 'Settings Version')
    auth_gae_apps = ListField(str, 'Authorized App Engine IDs')
    tier = Field(str, 'Tier')
    avail_type = Field(str, 'Availability Type')
    price_plan = Field(str, 'Pricing Plan')
    repl_type = Field(str, 'Replication Type')
    auto_resize_limit = Field(str, 'Storage Auto Resize Limit')
    storage_auto_resize = Field(bool, 'Storage Auto Resize Enabled')
    activation_policy = Field(str, 'Activation Policy')
    disk_type = Field(str, 'Data Disk Type')
    db_repl_enabled = Field(bool, 'Database Replication Enabled')
    crash_safe_repl_enabled = Field(bool, 'Crash-Safe Replication Enabled')
    disk_size_gb = Field(str, 'Data Disk Size (GB)')


class CloudSQLDatabase(SmartJsonClass):
    charset = Field(str, 'MySQL Charset Value')
    collation = Field(str, 'MySQL Collation Value')
    name = Field(str, 'Database Name')
    instance = Field(str, 'Cloud SQL Instance Name')
    self_link = Field(str, 'Resource URI')
    project_id = Field(str, 'Project ID')
    compat_level = Field(int, 'Compatibility Level')
    recov_model = Field(str, 'Recovery Model')


class MapObject(SmartJsonClass):
    key = Field(str, 'Key')
    value = Field(str, 'Value')


class SCCFinding(SmartJsonClass):
    name = Field(str, 'Name')
    state = Field(str, 'State', enum=SCC_FINDING_STATES)
    category = Field(str, 'Category')
    external_uri = Field(str, 'Information URI')
    event_time = Field(datetime.datetime, 'Event Time')
    create_time = Field(datetime.datetime, 'Creation Time')
    sec_marks = ListField(MapObject, 'Security Marks')
    sec_marks_name = Field(str, 'Security Marks Resource Name')


# pylint: disable=too-many-instance-attributes
class GceAdapter(AdapterBase, Configurable):
    class MyDeviceAdapter(DeviceAdapter):
        # Device type
        device_type = Field(str, 'Asset Type', enum=list(dev.name for dev in DeviceType))

        # generic things
        creation_time_stamp = Field(datetime.datetime, 'Creation Time Stamp')
        project_id = Field(str, 'Project ID')

        # COMPUTE things
        size = Field(str, 'Google Device Size')
        image = Field(str, 'Device image')
        cluster_name = Field(str, 'GCE Cluster Name')
        cluster_uid = Field(str, 'GCE Cluster Unique ID')
        cluster_location = Field(str, 'GCE Cluster Location')
        gce_tags = ListField(GceTag, 'GCE Metadata Tags')
        gce_labels = ListField(GceTag, 'GCE labels')
        gce_network_tags = ListField(str, 'GCE Network Tags')
        service_accounts = ListField(str, 'GCE Service Accounts')
        firewalls = ListField(GceFirewall, 'GCE Firewalls')

        # STORAGE things
        etag = Field(str, 'eTag')
        loc_type = Field(str, 'Location Type')
        updated = Field(datetime.datetime, 'Updated')
        bkt_id = Field(str, 'Bucket ID')
        metageneration = Field(str, 'Metageneration')
        loc = Field(str, 'Location')
        storage_class = Field(str, 'Storage Class')
        project_num = Field(int, 'Project Number')
        url = Field(str, 'API Self-Link')
        iam_config = Field(GCPBucketIamConf, 'Bucket IAM Config', json_format=JsonArrayFormat.table)
        object_count = Field(int, 'Storage Object Count')
        storage_objects = ListField(GCPStorageObject, 'Storage Objects', json_format=JsonArrayFormat.table)

        # SQL_DATABASE things
        self_link = Field(str, 'Resource URI')
        conn_name = Field(str, 'Connection Name',
                          description='Connection name of the Cloud SQL isntance used in connection strings')
        region = Field(str, 'Region')
        gce_zone = Field(str, 'Compute Engine Zone',
                         description='The Compute Engine zone that the instance is currently serving from. '
                                     'This value could be different from the zone that was specified when '
                                     'the instance was created if the instance has failed over to its secondary zone.')
        scheduled_maintenance = Field(datetime.datetime, 'Upcoming Scheduled Maintenance')
        master_inst_name = Field(str, 'Master Instance Name')
        inst_type = Field(str, 'Instance Type', enum=SQL_INSTANCE_TYPES)
        suspend_reason = Field(str, 'Suspension Reason', enum=SQL_SUSP_REASONS)
        repl_names = ListField(str, 'Replica Names')
        db_version = Field(str, 'Database Version', enum=SQL_DB_VERSIONS)
        inst_state = Field(str, 'State', enum=SQL_INSTANCE_STATES)
        db_settings = Field(CloudSQLSettings, 'Database Settings')
        databases = ListField(CloudSQLDatabase, 'Databases')

        # SCC_ASSET things
        resource_name_full = Field(str, 'Resource Name')
        resource_name_relative = Field(str, 'Relative Resource Name')
        res_props = ListField(MapObject, 'Resource Properties')
        res_parent = Field(str, 'Resource Parent')
        res_type = Field(str, 'Resource Type')
        res_proj = Field(str, 'Resource Project')
        res_owners = ListField(str, 'Resource Owners')
        res_display_name = Field(str, 'Resource Display Name')
        res_proj_display_name = Field(str, 'Resource Project Display Name')
        res_parent_display_name = Field(str, 'Resource Parent Display Name')
        scc_findings = ListField(SCCFinding, 'SCC Findings')
        sec_marks = ListField(MapObject, 'Security Marks')
        sec_marks_name = Field(str, 'Security Marks Resource Name')

    class MyUserAdapter(UserAdapter):
        project_ids = ListField(str, 'Project IDs')
        roles = ListField(str, 'Roles')
        gcp_user_type = Field(str, 'User Type')
        roles_perms = ListField(GCPUserRolePerms, 'Role Details')

    def __init__(self):
        super().__init__(get_local_config_file(__file__))

    def _get_client_id(self, client_config):
        auth_file = json.loads(self._grab_file_contents(client_config['keypair_file']))
        return auth_file['client_id'] + '_' + auth_file['project_id']

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(GCE_ENDPOINT_FOR_REACHABILITY_TEST)

    def _connect_client(self, client_config):
        try:
            client = GoogleCloudPlatformConnection(
                service_account_file=json.loads(self._grab_file_contents(client_config['keypair_file'])),
                fetch_storage=self.__fetch_buckets,
                fetch_roles=self.__get_roles,
                fetch_cloud_sql=self.__fetch_cloud_sql,
                scc_orgs=self.__scc_orgs,
                https_proxy=client_config.get('https_proxy')
            )
            with client:
                projects = next(client.get_project_list())
                if not projects:
                    raise ClientConnectionException(f'No projects found. Please check the service account permissions')
                if self.__get_roles:
                    try:
                        self.__predefined_roles = list(client.get_predefined_roles())
                    except Exception:
                        logger.warning(f'Failed to fetch roles. Make sure permissions are correct.', exc_info=True)
                        self.__predefined_roles = list()
                return client, client_config
        except Exception as e:
            client_id = self._get_client_id(client_config)
            logger.error(f'Failed to connect to client {client_id}')
            raise ClientConnectionException(f'Error: {e}')

    def _query_devices_by_client(self, client_name: str,
                                 client_data: Tuple[GoogleCloudPlatformConnection, dict]):
        """
        XXX: Add your own device querying here!
        :param client_name: string client name
        :param client_data: gcp connection object and client dict
        :return:
        """
        yield from self._query_compute_devices_by_client(client_name, client_data)
        if self.__fetch_buckets:
            yield from self._query_storage_devices_by_client(client_name, client_data)
        if self.__fetch_cloud_sql:
            yield from self._query_database_devices_by_client(client_name, client_data)
        if self.__scc_orgs:
            yield from self._query_scc_assets_by_client(client_name, client_data)

    # pylint: disable=arguments-differ
    def _query_users_by_client(self,
                               client_name: str,
                               client_data: Tuple[GoogleCloudPlatformConnection, dict]):
        client, client_dict = client_data
        with client:
            all_projects = list(client.get_project_list())
            for i, project in enumerate(all_projects):
                try:
                    project_id = project.get('projectId')
                    logger.info(f'Users: handling project {i}/{len(all_projects)} - {project_id}')
                    all_iam_data = list(client.get_user_list(project_id))
                    try:
                        role_data = list(client.get_project_roles(project_id)) if self.__get_roles else []
                    except Exception:
                        logger.warning(f'Failed to get roles for project {project_id}')
                        role_data = list()
                    yield all_iam_data, role_data, project
                except Exception:
                    logger.exception(f'Error while fetching users for project {project.get("projectId")}')

    @staticmethod
    def __get_firewalls(provider):
        try:
            # Libcloud does not support 'disabled' firewalls so we have to do this ourselves
            response = provider.connection.request('/global/firewalls', method='GET').object
            # Libcloud also does not support destRanges so we have to support that as well.
            firewalls = []
            for f in response.get('items', []):
                if f.get('disabled'):
                    continue
                fw = provider._to_firewall(f)  # pylint: disable=protected-access
                if f.get('destinationRanges'):
                    fw.extra['destinationRanges'] = f.get('destinationRanges')
                firewalls.append(fw)
            return firewalls
        except Exception:
            logger.exception(f'Can not get firewalls')
            return []

    @staticmethod
    def __get_compute_provider(auth_json, project=None, proxy_url=None):
        return get_driver(Provider.GCE)(
            auth_json['client_email'],
            auth_json['private_key'],
            project=project or auth_json['project_id'],
            proxy_url=proxy_url
        )

    def _query_database_devices_by_client(self, client_name: str,
                                          client_data: Tuple[GoogleCloudPlatformConnection, dict]):
        client, client_config = client_data
        auth_json = json.loads(self._grab_file_contents(client_config['keypair_file']))
        try:
            with client:
                try:
                    for db_instance in client.get_databases():
                        yield {
                            'type': DeviceType.DATABASE,
                            'device_data': (db_instance,)
                        }
                except Exception:
                    logger.warning(f'Failed to get databases for all projects. '
                                   f'Attempting alternate...',
                                   exc_info=True)
                    for db_instance in client.get_databases(auth_json['project_id']):
                        yield {
                            'type': DeviceType.DATABASE,
                            'device_data': (db_instance,)
                        }
        except Exception:
            logger.exception(f'Failed to get databases for {client_name}')
            yield {}

    def _query_storage_devices_by_client(self, client_name: str,
                                         client_data: Tuple[GoogleCloudPlatformConnection, dict]):
        client, client_config = client_data
        auth_json = json.loads(self._grab_file_contents(client_config['keypair_file']))
        try:
            with client:
                try:
                    for bucket in client.get_storage_list(get_bucket_objects=self.__fetch_bkt_objects):
                        yield {
                            'type': DeviceType.STORAGE,
                            'device_data': (bucket,)
                        }
                except Exception:
                    logger.warning(f'Failed to get storage devices for all projects. '
                                   f'Attempting alternate...',
                                   exc_info=True)
                    for bucket in client.get_storage_list(get_bucket_objects=self.__fetch_bkt_objects,
                                                          project_id=auth_json['project_id']):
                        yield {
                            'type': DeviceType.STORAGE,
                            'device_data': (bucket,)
                        }
        except Exception:
            logger.exception(f'Failed to get storage objects for {client_name}')
            yield {}

    def _query_compute_devices_by_client(self, client_name: str,
                                         client_data: Tuple[GoogleCloudPlatformConnection, dict]):
        client, client_config = client_data
        auth_json = json.loads(self._grab_file_contents(client_config['keypair_file']))
        try:
            with client:
                all_projects = list(client.get_project_list())
            for i, project in enumerate(all_projects):
                logger.info(f'Handling project {i}/{len(all_projects)} - {project.get("projectId")}')
                try:
                    compute_provider = self.__get_compute_provider(
                        auth_json,
                        project.get('projectId'),
                        client_config.get('https_proxy')
                    )
                    firewalls = self.__get_firewalls(compute_provider)
                    for device_raw in compute_provider.list_nodes():
                        yield {
                            'type': DeviceType.COMPUTE,
                            'device_data': (device_raw, project.get('projectId'), firewalls)
                        }
                except Exception as e:
                    message = f'Problem with project {project}: {str(e)}'
                    if 'error may be an authentication issue' in str(e):
                        logger.warning(message)
                    elif 'Compute Engine API has not been used in project' in str(e):
                        logger.warning(f'Problem with project {project}: Compute API not enabled')
                    else:
                        logger.warning(message, exc_info=True)
        except Exception:
            logger.exception(f'exception in getting all projects. using alternative path')
            provider = self.__get_compute_provider(auth_json, None,
                                                   client_config.get('https_proxy'))
            firewalls = self.__get_firewalls(provider)
            for device_raw in provider.list_nodes():
                yield {
                    'type': DeviceType.COMPUTE,
                    'device_data': (device_raw, auth_json['project_id'], firewalls)
                }

    @staticmethod
    def _query_scc_assets_by_client(client_name: str,
                                    client_data: Tuple[GoogleCloudPlatformConnection, dict]):
        client, client_config = client_data
        try:
            with client:
                for scc_asset in client.get_scc_assets():
                    yield {
                        'type': DeviceType.SCC_ASSET,
                        'device_data': (scc_asset,)
                    }
        except Exception:
            logger.exception(f'Failed to get scc assets for {client_name}')
            yield {}

    @classmethod
    def _db_config_schema(cls) -> dict:
        return {
            'items': [
                {
                    'name': 'fetch_cloud_sql',
                    'type': 'bool',
                    # 'description': 'Note: The Google Cloud SQL API is currently in BETA.'
                    'title': 'Fetch Google Cloud SQL database instances'
                },
                {
                    'name': 'fetch_buckets',
                    'type': 'bool',
                    'title': 'Fetch Google Cloud Storage buckets'
                },
                {
                    'name': 'fetch_bucket_objects',
                    'type': 'bool',
                    'title': 'Fetch Object metadata in Google Cloud Storage buckets'
                },
                {
                    'name': 'match_role_permissions',
                    'type': 'bool',
                    'title': 'Fetch IAM permissions for users'  # Requires iam.roles.list IAM permission
                },
                {
                    'name': 'scc_orgs',
                    'type': 'string',
                    'title': 'Security Command Center Organizations',
                    # 'description': 'Requires organization-level securitycenter.x.list permissions '
                }
            ],
            'required': [
                'fetch_cloud_sql',
                'fetch_buckets',
                'fetch_bucket_objects',
                'match_role_permissions'
            ],
            'pretty_name': 'Google Cloud Platform configuration',
            'type': 'array'
        }

    @classmethod
    def _db_config_default(cls) -> dict:
        return {
            'fetch_buckets': False,
            'fetch_bucket_objects': False,
            'match_role_permissions': False,
            'fetch_cloud_sql': False,
            'scc_orgs': '',
        }

    def _on_config_update(self, config):
        logger.info(f'Loading GCP config: {config}')
        self.__fetch_buckets = config['fetch_buckets']
        self.__fetch_cloud_sql = config['fetch_cloud_sql']
        self.__fetch_bkt_objects = config['fetch_bucket_objects']
        self.__get_roles = config['match_role_permissions']
        self.__scc_orgs = config.get('scc_orgs', '')

    @staticmethod
    def _clients_schema():
        return {
            'items': [
                {
                    'name': 'keypair_file',
                    'title': 'JSON Key pair for the service account',
                    'description': 'The binary contents of the JSON keypair file',
                    'type': 'file',
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'keypair_file'
            ],
            'type': 'array'
        }

    def create_device(self, device_dict, *args, **kwargs):
        dev_type = device_dict['type']
        device_data = device_dict['device_data']
        if dev_type == DeviceType.COMPUTE:
            create_device = self.create_compute_device
            # return self.create_compute_device(*device_data, *args, **kwargs)
        elif dev_type == DeviceType.STORAGE:
            create_device = self.create_storage_device
            # return self.create_storage_device(*device_data, *args, **kwargs)
        elif dev_type == DeviceType.DATABASE:
            create_device = self.create_database_device
        elif dev_type == DeviceType.SCC_ASSET:
            create_device = self.create_scc_asset_device
        else:
            create_device = None
        if create_device:
            return create_device(*device_data, *args, **kwargs)
        logger.warning(f'Unknown device type: {dev_type}. '
                       f'Cannot process device data {device_data}')
        return None

    # pylint:disable=too-many-statements
    def create_scc_asset_device(self, device_raw, *args, **kwargs):
        try:
            device = self._new_device_adapter()
            scc_props = device_raw.get('securityCenterProperties')
            if not isinstance(scc_props, dict):
                logger.warning(f'Got bad scc props for asset {device_raw}, '
                               f'expected dict and got instead {scc_props}')
                return None
            device_id = scc_props.get('resourceName')
            if not device_id:
                logger.warning(f'Bad device with no ID: {device_raw}')
                return None
            # generic Axonius stuff
            device_org = device_raw.get('organization_id')
            device.id = f'{device_org}_{device_id}'
            device.cloud_provider = 'GCP'
            device.name = device_raw.get('name')
            device.cloud_id = device_id
            if isinstance(scc_props.get('owners'), list) and scc_props.get('owners'):
                device.owner = str(scc_props.get('owners')[0])
                device.res_owners = list(str(owner) for owner in scc_props.get('owners'))
            device.first_seen = parse_date(device_raw.get('createTime'))
            device.last_seen = parse_date(device_raw.get('updateTime'))
            # These fields are correlatable and unique to each GCP device!
            device.resource_name_full = device_id
            # relative name example: organizations/{organization_id}/assets/{asset_id}
            device.resource_name_relative = device_raw.get('name')
            # full name example: //library.googleapis.com/shelves/shelf1/books/book2
            device.device_type = DeviceType.SCC_ASSET.name
            device.creation_time_stamp = parse_date(device_raw.get('createTime'))
            device.updated = parse_date(device_raw.get('updateTime'))
            res_props_dict = device_raw.get('resourceProperties')
            if isinstance(res_props_dict, dict):
                res_props = list()
                for key, value in res_props_dict.items():
                    res_props.append(MapObject(key=key, value=value))
                device.res_props = res_props
            else:
                logger.warning(f'Failed to parse resource properties of {device_id} from {res_props_dict}')
            device.res_parent = scc_props.get('resourceParent')
            device.res_type = scc_props.get('resourceType')
            device.res_proj = scc_props.get('resourceProject')
            device.res_display_name = scc_props.get('resourceDisplayName')
            device.res_proj_display_name = scc_props.get('resourceProjectDisplayName')
            device.res_parent_display_name = scc_props.get('resourceParentDisplayName')
            findings_raw = device_raw.get('findings')
            if isinstance(findings_raw, list):
                findings_list = list()
                for finding_raw in findings_raw:
                    state = finding_raw.get('state')
                    if state not in SCC_FINDING_STATES:
                        state = None
                        logger.warning(f'Invalid SCC Finding state: {state}')
                    finding = SCCFinding(
                        name=finding_raw.get('name'),
                        state=state,
                        category=finding_raw.get('category'),
                        external_url=finding_raw.get('externalUri'),
                        event_time=parse_date(finding_raw.get('eventTime')),
                        create_time=parse_date(finding_raw.get('createTime'))
                    )
                    self._parse_security_marks(finding, finding_raw.get('securityMarks'))
                    findings_list.append(finding)
                device.scc_findings = findings_list
            sec_marks = device_raw.get('securityMarks')
            self._parse_security_marks(device, sec_marks)
            device.set_raw(device_raw)
        except Exception:
            # remove objects to make device_raw not hueg
            _ = device_raw.pop('findings', None)
            logger.exception(f'Failed to create scc asset device for {device_raw}')
            device = None
        return device

    @staticmethod
    def _parse_security_marks(target_obj, marks_dict):
        if not isinstance(marks_dict, dict):
            logger.warning(f'Failed to parse security marks from {marks_dict}')
            return
        marks_name = marks_dict.get('name')
        if not marks_name:
            logger.warning(f'Failed to parse security marks from {marks_dict}')
            return
        marks_list = list()
        if isinstance(marks_dict.get('marks'), dict):
            for key, value in marks_dict.get('marks', {}).items():
                marks_list.append(MapObject(key=key, value=value))
        else:
            logger.warning(f'Failed to parse security marks from {marks_dict}')
            return
        target_obj.sec_marks_name = marks_name
        target_obj.sec_marks = marks_list

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def create_database_device(self, device_raw, *args, **kwargs):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('masterInstanceName')
            if not device_id:
                logger.warning(f'Bad device with no ID: {device_raw}')
                return None
            # generic Axonius stuff
            project_id = device_raw.get('project')
            device.id = f'{device_id}_{project_id}_{device_raw.get("name")}'
            device.cloud_provider = 'GCP'
            device.name = device_raw.get('name')
            device.email = device_raw.get('serviceAccountEmailAddress')

            try:
                total_size = device_raw.get('maxDiskSize') or 0
                curr_size = device_raw.get('currentDiskSize') or 0
                free_size = total_size - curr_size
                device.add_hd(
                    total_size=total_size,
                    free_size=free_size)
            except Exception:
                logger.warning(f'Failed to add hd info to {device_id}')

            ips_list = list()
            ip_map_raw = device_raw.get('ipAddresses')
            if isinstance(ip_map_raw, list):
                for ip_mapping in ip_map_raw:
                    if not isinstance(ip_mapping, dict):
                        continue
                    ip = ip_mapping.get('ipAddress')
                    ip_type = ip_mapping.get('type', '')
                    if ip_type in ('OUTGOING', 'PRIMARY'):
                        try:
                            device.add_public_ip(ip)
                        except Exception:
                            logger.warning(f'Failed to add public ip {ip} for {device_id}')
                    ips_list.append(ip)
            ipv6 = device_raw.get('ipv6Address')
            if ipv6:
                ips_list.append(ipv6)

            try:
                device.add_ips_and_macs(ips=ips_list)
            except Exception:
                logger.exception(f'Failed to add IPs for device {device_raw}')

            # GCP specific stuff
            device.project_id = device_raw.get('project')
            device.device_type = DeviceType.DATABASE.name

            # DATABASE specific stuff
            device.etag = device_raw.get('etag')
            device.self_link = device_raw.get('selfLink')
            device.region = device_raw.get('region')
            device.conn_name = device_raw.get('connectionName')
            device.gce_zone = device_raw.get('gceZone')
            device.master_inst_name = device_raw.get('masterInstanceName')

            try:
                device.inst_type = device_raw.get('instanceType')
            except Exception as e:
                logger.warning(f'Failed to parse instance type. got {str(e)}')

            try:
                device.suspend_reason = device_raw.get('suspensionReason')
            except Exception as e:
                logger.warning(f'Failed to parse suspend reason, got {str(e)}')

            repl_names = device_raw.get('replicaNames')
            if repl_names and isinstance(repl_names, list):
                device.repl_names = repl_names

            try:
                device.db_version = device_raw.get('databaseVersion')
            except Exception as e:
                logger.warning(f'Failed to parse db version, got {str(e)}')

            try:
                device.inst_state = device_raw.get('state')
            except Exception as e:
                logger.warning(f'Failed to parse instance state, got {str(e)}')

            try:
                maintenance_dict = device_raw.get('scheduledMaintenance') or {}
                device.scheduled_maintenance = parse_date(maintenance_dict.get('startTime'))
            except Exception:
                logger.warning(f'Failed to parse scheduled maintenance data for {device_id}')

            try:
                db_settings = device_raw.get('settings') or {}
                if not db_settings:
                    raise KeyError('settings')
                auto_resize = db_settings.get('storageAutoResize')
                if not isinstance(auto_resize, bool):
                    auto_resize = None
                repl_enabled = db_settings.get('databaseReplicationEnabled')
                if not isinstance(repl_enabled, bool):
                    repl_enabled = None
                crash_repl_enabled = db_settings.get('crashSafeReplicationEnabled')
                if not isinstance(crash_repl_enabled, bool):
                    crash_repl_enabled = None

                auth_gae_apps = db_settings.get('authorizedGaeApplications')
                if not isinstance(auth_gae_apps, list):
                    auth_gae_apps = None
                device.db_settings = CloudSQLSettings(
                    ver=db_settings.get('settingsVersion'),
                    auth_gae_apps=auth_gae_apps,
                    tier=db_settings.get('tier'),
                    avail_type=db_settings.get('availabilityType'),
                    price_plan=db_settings.get('pricingPlan'),
                    repl_type=db_settings.get('replicationType'),
                    auto_resize_limit=db_settings.get('storageAutoResizeLimit'),
                    activation_policy=db_settings.get('activationPolicy'),
                    storage_auto_resize=auto_resize,
                    disk_type=db_settings.get('dataDiskType'),
                    db_repl_enabled=repl_enabled,
                    crash_safe_repl_enabled=crash_repl_enabled,
                    disk_size_gb=db_settings.get('dataDiskSizeGb')
                )
            except Exception:
                logger.warning(f'Failed to parse database settings for {device_id}')

            databases_list_raw = device_raw.get('databases') or []
            if databases_list_raw and isinstance(databases_list_raw, list):
                databases = list()
                for db in databases_list_raw:
                    try:
                        settings = db.get('sqlserverDatabaseDetails') or {}
                        if not settings:
                            continue
                        try:
                            compat_level = int(settings.get('compatibilityLevel'))
                        except Exception:
                            compat_level = None
                        databases.append(CloudSQLDatabase(
                            charset=db.get('charset'),
                            collation=db.get('collation'),
                            name=db.get('name'),
                            instance=db.get('instance'),
                            self_link=db.get('selfLink'),
                            project_id=db.get('project'),
                            compat_level=compat_level,
                            recov_model=settings.get('recoveryModel')
                        ))
                    except Exception:
                        logger.exception(f'Failed to get database information from {device_raw}')
                device.databases = databases
            # raw (json)
            device.set_raw(device_raw)
        except Exception:
            # remove objects to make device_raw not hueg
            logger.exception(f'Failed to create database device for {device_raw}')
            device = None
        return device

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def create_storage_device(self, device_raw, *args, **kwargs):
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if not device_id:
                logger.warning(f'Bad device with no ID: {device_raw}')
                return None
            # generic Axonius stuff
            project_id = device_raw.get('projectId')
            device.id = f'{device_id}_{project_id}_{device_raw.get("name")}'
            device.cloud_provider = 'GCP'
            device.name = device_raw.get('name')

            # GCP specific stuff
            device.project_id = device_raw.get('projectId')
            device.device_type = DeviceType.STORAGE.name
            device.creation_time_stamp = parse_date(device_raw.get('timeCreated'))

            # STORAGE specific stuff
            device.etag = device_raw.get('etag')
            device.loc_type = device_raw.get('locationType')
            device.metageneration = device_raw.get('metageneration')
            device.bkt_id = device_raw.get('id')
            device.loc = device_raw.get('location')
            device.updated = parse_date(device_raw.get('updated'))
            try:
                device.project_num = int(device_raw.get('projectNumber'))
            except Exception:
                logger.debug(f'Failed to get device project num for {device_raw}', exc_info=True)
            device.storage_class = device_raw.get('storageClass')
            device.url = device_raw.get('selfLink')
            iam_dict = device_raw.get('iamConfiguration') or {}
            if iam_dict:
                try:
                    device.iam_config = GCPBucketIamConf(
                        uniform_blaccess=iam_dict.get('uniformBucketLevelAccess').get('enabled'),
                        bucket_policy_only=iam_dict.get('bucketPolicyOnly').get('enabled')
                    )
                except Exception:
                    logger.warning(f'Failed to add iam configuration for device: {device_raw}',
                                   exc_info=True)

            # Handle storage container objects
            if not isinstance(device_raw.get('x_objects'), list):
                logger.warning(f'Expected a list of objects for device {device_id}, '
                               f'got instead {device_raw.get("x_objects")}')
                device_raw['x_objects'] = []
            storage_object_metadata = device_raw.get('x_objects')
            device.object_count = len(storage_object_metadata)
            # Trim object metadata to prevent super huge data
            if storage_object_metadata:
                device_raw['x_objects'] = storage_object_metadata[:10]
            for object_raw in device_raw.get('x_objects'):
                try:
                    device.storage_objects.append(GCPStorageObject(
                        content_type=object_raw.get('contentType') or '',
                        name=object_raw.get('name') or '',
                        etag=object_raw.get('etag') or '',
                        generation=object_raw.get('generation') or '',
                        md5_hash=object_raw.get('md5Hash') or '',
                        modified=parse_date(object_raw.get('updated')),
                        crc32c=object_raw.get('crc32c') or '',
                        metageneration=object_raw.get('metageneration') or '',
                        media_url=object_raw.get('mediaLink') or '',
                        size=int(object_raw.get('size', 0) or 0),
                        created=parse_date(object_raw.get('timeCreated')),
                        id=object_raw.get('id') or '',
                        self_link=object_raw.get('selfLink') or '',
                        storage_class=object_raw.get('storageClass') or '',
                        storage_class_updated=parse_date(object_raw.get('timeStorageClassUpdated'))
                    ))
                except Exception:
                    message = f'Failed to add storage object for device {device_id}'
                    logger.exception(message)
                    continue
            # raw (json)
            device.set_raw(device_raw)
        except Exception:
            # remove objects to make device_raw not hueg
            device_raw.pop('x_objects', None)
            logger.exception(f'Failed to create storage device for {device_raw}')
            device = None
        return device

    # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-nested-blocks
    def create_compute_device(self, raw_device_data, project_id, firewalls: List[GCEFirewall], *args, **kwargs):
        device = self._new_device_adapter()
        device.device_type = DeviceType.COMPUTE.name
        device.id = raw_device_data.id
        device.cloud_provider = 'GCP'
        device.cloud_id = device.id
        device.project_id = project_id
        self._compute_device_parse_generic(device, raw_device_data)
        self._compute_device_parse_metadata(device, raw_device_data)

        gce_network_tags = []
        try:
            gce_network_tags = raw_device_data.extra.get('tags') or []
            device.gce_network_tags = gce_network_tags
        except Exception:
            logger.exception(f'Can not get gce network tags for instance')

        device_service_accounts = []
        try:
            device.service_accounts = []
            service_accounts_raw = raw_device_data.extra.get('serviceAccounts')
            if isinstance(service_accounts_raw, list) and service_accounts_raw:
                for service_account_raw in service_accounts_raw:
                    try:
                        if service_account_raw.get('email'):
                            device_service_accounts.append(service_account_raw.get('email'))
                    except Exception:
                        logger.exception(f'Problem with service account {service_account_raw}')

            device.service_accounts = device_service_accounts
        except Exception:
            logger.exception(f'Problem adding Service Accounts')

        self._compute_device_parse_firewalls(device, device_service_accounts, firewalls,
                                             gce_network_tags, raw_device_data)

        try:
            # some fields might not be basic types
            # by using IgnoreErrorJSONEncoder with JSON encode we verify that this
            # will pass a JSON encode later by mongo
            device.set_raw(json.loads(json.dumps(
                raw_device_data.__dict__, cls=IgnoreErrorJSONEncoder)))
        except Exception:
            logger.exception(f'Can\'t set raw for {str(device.id)}')
        return device

    @staticmethod
    def _compute_device_parse_firewalls(device, device_service_accounts, firewalls,
                                        gce_network_tags, raw_device_data):
        # Try to find matching firewalls
        try:
            # Matching can be done by ip, service account, or tag.
            instance_ips = list(raw_device_data.private_ips) + list(raw_device_data.public_ips)
            instance_networks = []
            for network_interface in (raw_device_data.extra.get('networkInterfaces') or []):
                if network_interface.get('network'):
                    instance_networks.append(network_interface.get('network').split('/')[-1])
            device.firewalls = []
            for fw in firewalls:
                # Validate that this instance is in the network the fw is valid for
                if fw.network.name not in instance_networks:
                    continue
                matched_by = []
                # We are searching for a match in all rules.
                # As explain in https://cloud.google.com/vpc/docs/firewalls, in both ingress and egress fw's the target
                # talks about the instances in the network.

                if not fw.target_ranges and not fw.target_tags and not fw.target_service_accounts:
                    matched_by.append(f'All instances in network')
                else:
                    for instance_ip in instance_ips:
                        for subnet in (fw.target_ranges or []):
                            try:
                                if '/' not in subnet:
                                    subnet += '/32'  # its a regular ip, lets add a subnet suffix
                                if ipaddress.ip_address(instance_ip) in ipaddress.ip_network(subnet):
                                    matched_by.append(f'Instance IP {instance_ip}')
                            except Exception:
                                logger.exception(f'Could not match by ingress ip/subnet')

                    for network_tag in gce_network_tags:
                        if network_tag in (fw.target_tags or []):
                            matched_by.append(f'Network tag {network_tag}')

                    for gce_service_account in device_service_accounts:
                        if gce_service_account in (fw.target_service_accounts or []):
                            matched_by.append(f'Service Account {gce_service_account}')

                if matched_by:
                    rules = []
                    for rule in (fw.allowed or []):
                        rules.append(GceFirewallRule(
                            type='Allowed',
                            protocol=rule.get('IPProtocol'),
                            ports=rule.get('ports') or []
                        ))
                    for rule in (fw.denied or []):
                        rules.append(GceFirewallRule(
                            type='Denied',
                            protocol=rule.get('IPProtocol'),
                            ports=rule.get('ports') or []
                        ))

                    source_ranges = [f'{tr}/32' if '/' not in tr else tr for tr in (fw.source_ranges or [])]
                    target_ranges = [f'{tr}/32' if '/' not in tr else tr for tr in (fw.target_ranges or [])]
                    destination_ranges = [f'{tr}/32' if '/' not in tr else tr for tr in
                                          (fw.extra.get('destinationRanges') or [])]
                    device.firewalls.append(GceFirewall(
                        name=fw.name,
                        direction=fw.direction or 'INGRESS',  # if not specified, documentation says its ingress.
                        priority=fw.priority,
                        match=matched_by,
                        source_ranges=source_ranges,
                        source_tags=fw.source_tags or [],
                        source_service_accounts=fw.source_service_accounts or [],
                        destination_ranges=destination_ranges,
                        target_ranges=target_ranges,
                        target_tags=fw.target_tags or [],
                        target_service_accounts=fw.target_service_accounts or [],
                        rules=rules
                    ))

                    # Add to a generic table
                    if fw.direction == 'EGRESS':
                        targets = destination_ranges
                    else:
                        # must be ingress according to gcp docs
                        targets = source_ranges + (fw.source_tags or []) + (fw.source_service_accounts or [])
                        targets = targets if targets else 'ALL'

                    for target in targets:
                        for rule in rules:
                            try:
                                protocol = rule.protocol
                            except Exception:
                                protocol = ''

                            try:
                                ports = rule.ports
                            except Exception:
                                ports = []

                            # No ports. Its important to still have None here
                            # or otherwise we won't have the rule at all
                            ports = ports if ports else [None]

                            for port in ports:
                                try:
                                    from_port, to_port = port.split('-')
                                except Exception:
                                    # Assume this is just a number and not a range
                                    from_port, to_port = port, port

                                try:
                                    if fw.direction.upper() in ['INGRESS', 'EGRESS']:
                                        direction = fw.direction.upper()
                                    else:
                                        direction = None
                                except Exception:
                                    direction = None
                                device.add_firewall_rule(
                                    name=fw.name,
                                    source='GCE Firewall Rule',
                                    type='Allow' if rule.type == 'Allowed' else 'Deny',
                                    direction=direction,
                                    target=target,
                                    protocol=protocol,
                                    from_port=from_port,
                                    to_port=to_port
                                )
        except Exception:
            logger.exception(f'Could not parse matching firewalls for instance')

    @staticmethod
    def _compute_device_parse_metadata(device, raw_device_data):
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
                        logger.exception(f'Problem getting extra tags for {raw_device_data}')
        except Exception:
            logger.exception(f'Problem getting cluster info for {str(raw_device_data)}')
        try:
            for key, value in (raw_device_data.extra.get('labels') or {}).items():
                device.gce_labels.append(GceTag(gce_key=key, gce_value=value))
        except Exception:
            logger.exception(f'Problem adding gce labels to instance')

    @staticmethod
    def _compute_device_parse_generic(device, raw_device_data):
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
                        device.add_nic(ips=[ip])
                        device.add_public_ip(ip)
        except Exception:
            logger.exception(f'Problem getting public IP for {str(raw_device_data)}')

    def _parse_raw_data(self, devices_raw_data):
        for device_dict in iter(devices_raw_data):
            if not device_dict:
                continue
            try:
                # device = self.create_device(raw_device_data, project_id, firewalls)
                device = self.create_device(device_dict)
                if device:
                    yield device
            except Exception:
                logger.exception(f'Got exception for raw_device_data: {device_dict}')

    # pylint: disable=undefined-variable
    def create_user_entity(self) -> MyUserAdapter:
        return self._new_user_adapter()

    def _find_user_role(self, role_raw, project_roles):
        for predef_role in self.__predefined_roles:
            if predef_role['name'] == role_raw:
                return predef_role
        for proj_role_list in project_roles.values():
            for proj_role in proj_role_list:
                if proj_role['name'] == role_raw:
                    return proj_role
        return None

    # pylint: disable=arguments-differ
    def _parse_users_raw_data(self, all_data: Iterable[Tuple[list, dict]]) -> Iterable[UserAdapter]:
        # First parse users for all projects. because the same user can be in different projects
        users_info = dict()
        roles_per_project = dict()
        for (all_iam_data, project_roles, project) in all_data:
            roles_per_project[project['projectId']] = project_roles
            for policy_role in all_iam_data:
                if not policy_role.get('role'):
                    logger.warning(f'Bad role: {policy_role}')
                    continue
                for member in (policy_role.get('members') or []):
                    if member not in users_info:
                        users_info[member] = defaultdict(list)
                    users_info[member]['roles'].append(policy_role.get('role'))
                    if project['projectId'] not in users_info[member]['projects']:
                        users_info[member]['projects'].append(project['projectId'])

        for user_id, user_info in users_info.items():
            try:
                user = self.create_user_entity()
                user.id = user_id
                try:
                    user.username = user_id.split(':')[1]
                except Exception:
                    user.username = user_id
                user.project_ids = user_info.get('projects') or None
                if self.__get_roles:
                    for role in user_info.get('roles'):
                        role_dict = self._find_user_role(role, roles_per_project)
                        if not (role_dict and isinstance(role_dict, dict)):
                            logger.debug(f'Failed to get permission details for role {role}')
                            continue
                        try:
                            if not user.roles_perms:
                                user.roles_perms = list()
                            user.roles_perms.append(
                                GCPUserRolePerms(
                                    name=role_dict.get('name'),
                                    title=role_dict.get('title'),
                                    descr=role_dict.get('description'),
                                    perms=role_dict.get('includedPermissions'),
                                    deleted=role_dict.get('deleted')
                                )
                            )
                        except Exception as e:
                            logger.warning(f'Error {str(e)} when parsing role details for {role_dict}')
                            continue
                user.roles = user_info.get('roles')
                try:
                    gcp_user_type, mail = user_id.split(':')
                    user.mail = mail
                    user.gcp_user_type = gcp_user_type
                except Exception:
                    logger.exception(f'Could not parse user_type, email for user {user_id}')
                user.set_raw({})  # there is no specific raw for a user
                yield user
            except Exception:
                logger.exception(f'Failed parsing user')

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets, AdapterProperty.Cloud_Provider]
