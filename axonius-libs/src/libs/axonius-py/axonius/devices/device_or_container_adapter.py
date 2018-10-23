import logging
import datetime

from axonius.fields import Field, ListField, JsonStringFormat
from axonius.devices.device_adapter import DeviceAdapter
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import format_ip

logger = logging.getLogger(f'axonius.{__name__}')


class ContainerTaskOrPod(SmartJsonClass):
    connectivity = Field(str, 'Task Connectivity')
    cpu_units = Field(int, 'Task CPU Units')
    desired_status = Field(str, 'Task Desired Status')
    task_group = Field(str, 'Task Group')
    task_health_status = Field(str, 'Task Health status')
    task_last_status = Field(str, 'Task Last Status')
    task_launch_type = Field(str, 'Task Launch Type')
    task_memory_in_mb = Field(int, 'Task Memory (MB)')
    task_name = Field(str, 'Task Name')
    task_id = Field(str, 'Task ID/Arn')
    task_definition_id = Field(str, 'Task Definition ID/Arn')
    task_definition_name = Field(str, 'Task Definition Name')
    platform_version = Field(str, 'Platform Version')
    created_at = Field(datetime.datetime, 'Task Created At')
    connectivity_at = Field(datetime.datetime, 'Task Connectivity At')


class ContainerInstanceOrNode(SmartJsonClass):
    container_instance_id = Field(str, 'ID')
    container_instance_name = Field(str, 'Name')


class ContainerService(SmartJsonClass):
    service_name = Field(str, 'Service Name')
    service_id = Field(str, 'Service ID/Arn')
    service_status = Field(str, 'Service Status')


class ContainerNetworkBindings(SmartJsonClass):
    bind_ip = Field(str, 'IPs', converter=format_ip, json_format=JsonStringFormat.ip)
    container_port = Field(int, 'Container port')
    host_port = Field(int, 'Host port')
    name = Field(str, 'Name')
    protocol = Field(str, 'Protocol')


class DeviceOrContainerAdapter(DeviceAdapter):
    """ A definition for containers that a device is running on. """
    cluster_name = Field(str, 'Cluster Name')
    cluster_id = Field(str, 'Cluster ID/Arn')
    container_last_status = Field(str, 'Last Status')
    container_image = Field(str, 'Image')

    container_instance_or_node = Field(ContainerInstanceOrNode, 'Instance/Node')
    container_task_or_pod = Field(ContainerTaskOrPod, 'Task/Pod')
    container_service = Field(ContainerService, 'Service')

    container_network_bindings = ListField(ContainerNetworkBindings, 'Network Bindings')

    def set_instance_or_node(self, **kwargs):
        self.container_instance_or_node = ContainerInstanceOrNode(**kwargs)

    def set_task_or_pod(self, **kwargs):
        self.container_task_or_pod = ContainerTaskOrPod(**kwargs)

    def set_service(self, **kwargs):
        self.container_service = ContainerService(**kwargs)

    def add_network_binding(self, **kwargs):
        network_binding = ContainerNetworkBindings(**kwargs)
        self.container_network_bindings.append(network_binding)
