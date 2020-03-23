import datetime
import logging

from axonius.adapter_base import AdapterBase, AdapterProperty
from axonius.adapter_exceptions import ClientConnectionException
from axonius.clients.rest.connection import RESTConnection, RESTException
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.datetime import parse_date
from axonius.utils.files import get_local_config_file
from logicmonitor_adapter.client_id import get_client_id
from logicmonitor_adapter.connection import LogicmonitorConnection

logger = logging.getLogger(f'axonius.{__name__}')


class CustomPropertiesKeyValue(SmartJsonClass):
    """ A definition for a key value field of unknown/custom properties. """
    key = Field(str, 'Property Name')
    value = Field(str, 'Property Value')


class LogicmonitorAdapter(AdapterBase):
    # pylint: disable=too-many-instance-attributes
    class MyDeviceAdapter(DeviceAdapter):
        type = Field(int, 'Device Type')
        related_device_id = Field(int, 'Related Device ID')
        current_collector_id = Field(int, 'Current Collector ID')
        preferred_collector_id = Field(int, 'Preferred Collector ID')
        preferred_collector_group_id = Field(int, 'Preferred Collector Group ID')
        preferred_collector_group_name = Field(str, 'Preferred Collector Group Name')
        disable_alerting = Field(bool, 'Disable Alerting')
        auto_props_assigned_on = Field(datetime.datetime, 'Auto Properties Assigned On')
        auto_props_updated_on = Field(datetime.datetime, 'Auto Properties '
                                                         'Updated On')
        scan_config_id = Field(int, 'Scan Config ID')
        link = Field(str, 'Link')
        enable_netflow = Field(bool, 'Enable Netflow')
        netflow_collector_id = Field(int, 'Netflow Collector ID')
        netflow_collector_group_id = Field(int, 'Netflow Collector Group ID')
        netflow_collector_group_name = Field(str, 'Netflow Collector Group Name')
        last_data_time = Field(datetime.datetime, 'Last Data Time')
        last_raw_data_time = Field(datetime.datetime, 'Last Raw Data Time')
        host_group_ids = ListField(str, 'Host Group IDs')
        sdt_status = ListField(str, 'SDT Status')
        user_permission = Field(str, 'User Permission')
        host_status = Field(str, 'Host Status')
        alert_status = ListField(str, 'Alert Status')
        alert_status_priority = Field(int, 'Alert Status Priority')
        awsState = Field(int, 'AWS State')
        alert_disabled_status = ListField(str, 'Alert Disabled Status')
        alerting_disabled_on = Field(bool, 'Alerting Disabled On')
        collector_description = Field(str, 'Collector Description')
        netflow_collector_description = Field(str, 'Netflow Collector Description')
        uptime_in_seconds = Field(int, 'Uptime in Seconds')
        deleted_time_in_ms = Field(int, 'Deleted Time in Milliseconds')
        to_delete_time_in_ms = Field(int, 'Time to Delete in Milliseconds')
        has_disabled_subresource = Field(bool, 'Has Disabled Resource')
        manual_discovery_flags = Field(str, 'Manual Discovery Flags')
        custom_properties = ListField(CustomPropertiesKeyValue, 'Custom Properties')

    def __init__(self, *args, **kwargs):
        super().__init__(config_file_path=get_local_config_file(__file__), *args, **kwargs)

    @staticmethod
    def _get_client_id(client_config):
        return get_client_id(client_config)

    @staticmethod
    def _test_reachability(client_config):
        return RESTConnection.test_reachability(client_config.get('domain'),
                                                https_proxy=client_config.get('https_proxy'))

    @staticmethod
    def get_connection(client_config):
        connection = LogicmonitorConnection(domain=client_config.get('domain'),
                                            verify_ssl=client_config.get('verify_ssl'),
                                            https_proxy=client_config.get('https_proxy'),
                                            access_id=client_config.get('access_id'),
                                            access_key=client_config.get('access_key'))
        with connection:
            pass
        return connection

    def _connect_client(self, client_config):
        try:
            return self.get_connection(client_config)
        except RESTException as e:
            message = f'Error connecting to client with domain ' \
                      f'{client_config.get("domain")}, reason: {e}'
            logger.exception(message)
            raise ClientConnectionException(message)

    @staticmethod
    def _query_devices_by_client(client_name, client_data):
        """
        Get all devices from a specific  domain
        :param str client_name: The name of the client
        :param obj client_data: The data that represent a connection
        :return: A json with all the attributes returned from the Server
        """
        with client_data:
            yield from client_data.get_device_list()

    @staticmethod
    def _clients_schema():
        """
        The schema LogicmonitorAdapter expects from configs
        :return: JSON scheme
        """
        return {
            'items': [
                {
                    'name': 'domain',
                    'title': 'Hostname or IP Address',
                    'type': 'string'
                },
                {
                    'name': 'access_id',
                    'title': 'Access ID',
                    'type': 'string',
                },
                {
                    'name': 'access_key',
                    'title': 'Access Key',
                    'type': 'string',
                    'format': 'password'
                },
                {
                    'name': 'verify_ssl',
                    'title': 'Verify SSL',
                    'type': 'bool'
                },
                {
                    'name': 'https_proxy',
                    'title': 'HTTPS Proxy',
                    'type': 'string'
                }
            ],
            'required': [
                'domain',
                'access_id',
                'access_key',
                'verify_ssl'
            ],
            'type': 'array'
        }

    def _create_device(self, device_raw):
        # pylint: disable=too-many-statements
        try:
            device = self._new_device_adapter()
            device_id = device_raw.get('id')
            if device_id is None:
                logger.warning(f'Bad device with id {device_id} has no ID: {device_raw}')
                return None
            device.id = device_id + '_' + (device_raw.get('displayName') or '')
            device.set_raw(device_raw)

            device.hostname = device_raw.get('name')
            device.name = device_raw.get('displayName')
            device.first_seen = parse_date(device_raw.get('createdOn'))
            device.last_seen = parse_date(device_raw.get('updatedOn'))

            for sys_property in device_raw.get('customProperties'):
                if sys_property.get('name') == 'system.sysinfo':
                    device.figure_os(sys_property.get('value') or '')

                if sys_property.get('name') == 'system.ips':
                    for sys_nic in sys_property.get('value'):
                        device.add_nic(mac=sys_nic.get('mac'),
                                       ips=sys_nic.get('ip_address'))

            device.type = device_raw.get('deviceType')
            related = device_raw.get('relatedDeviceId')
            if related > -1:
                device.related_device_id = related
            device.current_collector_id = device_raw.get('currentCollectorId')
            device.preferred_collector_id = device_raw.get('preferredCollectorId')
            device.preferred_collector_group_id = device_raw.get('preferredCollectorGroupId')
            device.preferred_collector_group_name = device_raw.get(
                'preferredCollectorGroupName')
            device.description = device_raw.get('description')
            device.disable_alerting = device_raw.get('disableAlerting')
            device.auto_props_assigned_on = parse_date(device_raw.get('autoPropsAssignedOn'))
            device.auto_props_updated_on = parse_date(device_raw.get('autoPropsUpdatedOn'))
            device.scan_config_id = device_raw.get('scanConfigId')
            device.link = device_raw.get('link')
            device.enable_netflow = device_raw.get('enableNetflow')
            device.netflow_collector_id = device_raw.get('netflowCollectorId')
            device.netflow_collector_group_id = device_raw.get('netflowCollectorGroupId')
            device.netflow_collector_group_name = device_raw.get('netflowCollectorGroupName')
            device.last_data_time = parse_date(device_raw.get('lastDataTime'))
            device.last_raw_data_time = parse_date(device_raw.get('lastRawdataTime'))
            device.host_group_ids = device_raw.get('hostGroupIds').split(',')
            device.sdt_status = device_raw.get('sdtStatus').split('-')
            device.user_permission = device_raw.get('userPermission')
            device.host_status = device_raw.get('hostStatus')
            device.alert_status = device_raw.get('alertStatus').split('-')
            device.alert_status_priority = device_raw.get('alertStatusPriority')
            device.awsState = device_raw.get('awsState')
            device.alert_disabled_status = device_raw.get(
                'alertDisableStatus').split('-')
            device.alerting_disabled_on = device_raw.get('alertingDisabledOn')
            device.collector_description = device_raw.get('collectorDescription')
            device.netflow_collector_description = device_raw.get('netflowCollectorDescription')
            device.uptime_in_seconds = device_raw.get('upTimeInSeconds')
            device.deleted_time_in_ms = device_raw.get('deletedTimeInMs')
            device.to_delete_time_in_ms = device_raw.get('toDeleteTimeInMs')
            device.has_disabled_subresource = device_raw.get('hasDisabledSubResource')
            device.manual_discovery_flags = device_raw.get('manualDiscoveryFlags')

            for prop in device_raw.get('customProperties'):
                device.custom_properties.append(CustomPropertiesKeyValue(
                    key=prop.get('name'), value=prop.get('value')))

            return device
        except Exception:
            logger.exception(f'Problem with fetching LogicMonitor Device for {device_raw}')
            return None

    def _parse_raw_data(self, devices_raw_data):
        for device_raw in devices_raw_data:
            device = self._create_device(device_raw)
            if device:
                yield device

    @classmethod
    def adapter_properties(cls):
        return [AdapterProperty.Assets]
