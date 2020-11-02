import logging

import datetime
from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, JsonStringFormat, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.utils.parsing import format_ip, format_ip_raw

logger = logging.getLogger(f'axonius.{__name__}')


class Label(SmartJsonClass):
    name = Field(str, 'Name')
    value = Field(str, 'Value')


class OwnerReference(SmartJsonClass):
    uid = Field(str, 'UID')
    name = Field(str, 'Name')
    api_version = Field(str, 'API Version')
    block_owner_deletion = Field(bool, 'Block Owner Deletion')
    controller = Field(bool, 'Controller')
    kind = Field(str, 'Kind')


class VolumeMount(SmartJsonClass):
    name = Field(str, 'Name')
    read_only = Field(bool, 'Read Only')
    path = Field(str, 'Path')
    sub_path = Field(str, 'Sub Path')


class Pod(SmartJsonClass):
    cluster_name = Field(str, 'Cluster Name')
    pod_name = Field(str, 'Pod Name')
    node_name = Field(str, 'Node Name')
    pod_uid = Field(str, 'Pod UID')
    pod_generate_name = Field(str, 'Pod Generate Name')
    namespace = Field(str, 'Namespace')
    labels = ListField(Label, 'Labels')
    owner_references = ListField(OwnerReference, 'Owner References')
    resource_version = Field(str, 'Resource Version')
    pod_link = Field(str, 'Pod Link')
    dns_policy = Field(str, 'DNS Policy')
    priority = Field(int, 'Priority')
    restart_policy = Field(str, 'Restart Policy')
    scheduler_name = Field(str, 'Scheduler Name')
    service_account_name = Field(str, 'Service Account Name')
    termination_grace_period = Field(int, 'Termination Grace Period (seconds)')
    phase = Field(str, 'Phase')
    pod_ip = Field(str, 'Pod IP', converter=format_ip, json_format=JsonStringFormat.ip)
    pod_ip_raw = ListField(str, converter=format_ip_raw, hidden=True)
    qos_class = Field(str, 'QoS Class')
    start_time = Field(datetime.datetime, 'Start Time')

    def append_label(self, **kwargs):
        self.labels.append(Label(**kwargs))

    def append_owner_references(self, **kwargs):
        self.owner_references.append(OwnerReference(**kwargs))


class Container(SmartJsonClass):
    args = ListField(str, 'Arguments')
    image = Field(str, 'Image')
    image_pull_policy = Field(str, 'Image Pull Policy')
    termination_message_path = Field(str, 'Termination Message Path')
    termination_message_policy = Field(str, 'Termination Message Policy')
    volume_mounts = ListField(VolumeMount, 'Volume Mounts')
    working_dir = Field(str, 'Working Directory')
    ready = Field(bool, 'Ready')
    restart_count = Field(int, 'Restart Count')

    def append_volume_mount(self, **kwargs):
        self.volume_mounts.append(VolumeMount(**kwargs))


# Represents a k8s object (Pod,Container)
class KubernetesDeviceInstance(DeviceAdapter, Pod, Container):
    pass


def get_value_or_default(name, obj, expected_type):
    """
    :param name: The same name of the object (Just for getting informative log)
    :param obj: The object we want to verify
    :param expected_type: The expected type of the given object
    :return: The object itself or the default value of expected type
    """

    result = obj or expected_type()
    if not isinstance(result, expected_type):
        logger.debug(f'Got unexpected type for {name}, expected {expected_type}, but got {str(type(result))}')
        result = expected_type()

    return result
