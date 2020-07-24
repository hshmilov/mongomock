import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter
from rancher_adapter import consts


class NodeCondition(SmartJsonClass):
    status = Field(str, 'Status')
    type = Field(str, 'Type')
    message = Field(str, 'Message')
    reason = Field(str, 'Reason')


class RancherKV(SmartJsonClass):
    key = Field(str, 'Key')
    value = Field(str, 'Value')


class CustomConfig(SmartJsonClass):
    address = Field(str, 'Address')
    docker_socket = Field(str, 'Docker Socket')
    internal_address = Field(str, 'Internal Address')
    labels = ListField(RancherKV, 'Labels')
    ssh_cert = Field(str, 'SSH Cert')
    taints = ListField(str, 'Taints')
    user = Field(str, 'User')


class NodeTaint(RancherKV):
    effect = Field(str, 'Effect')
    time_added = Field(datetime.datetime, 'Date Added')


class OwnerReference(SmartJsonClass):
    api_version = Field(str, 'API Version')
    block_deletion = Field(bool, 'Block Deletion')
    controller = Field(bool, 'Controller')
    kind = Field(str, 'Kind')
    name = Field(str, 'Name')
    uid = Field(str, 'UID')


class RancherDeviceInstance(DeviceAdapter):
    applied_node_version = Field(int, 'Applied Node Version')
    imported = Field(bool, 'Imported')
    removed = Field(datetime.datetime, 'Removed')
    cluster_id = Field(str, 'Cluster ID')
    conditions = ListField(NodeCondition, 'Conditions')
    control_plane = Field(bool, 'Control Plane')
    creator_id = Field(str, 'Creator ID')
    custom_config = Field(CustomConfig, 'Custom Config')
    etcd = Field(bool, 'Etcd')
    namespace_id = Field(str, 'Namespace ID')
    node_pool_id = Field(str, 'Node Pool ID')
    node_taints = ListField(NodeTaint, 'Node Taints')
    node_template_id = Field(str, 'Node Template ID')
    requested_hostname = Field(str, 'Requested Hostname')
    state = Field(str, 'State')
    rancher_labels = ListField(RancherKV, 'Labels')
    annotations = ListField(RancherKV, 'Annotations')
    transitioning = Field(str, 'Transitioning', enum=consts.TRANSITIONING_ENUM_VALUES)
    transitioning_message = Field(str, 'Transitioning Message')
    unschedulable = Field(bool, 'Unschedulable')
    volumes_attached = ListField(str, 'Attached Volumes')
    volumes_in_use = ListField(str, 'Volumes In Use')
    worker = Field(bool, 'Worker')
    allocatable = ListField(RancherKV, 'Allocatable')
    capacity = ListField(RancherKV, 'Capacity')
    limits = ListField(RancherKV, 'Limits')
    owner_references = ListField(OwnerReference, 'Owner References')
    pod_cidrs = ListField(str, 'Pod CIDR')
    provider_id = Field(str, 'Provider ID')
    requested = ListField(RancherKV, 'Requested')
    ssh_user = Field(str, 'sshUser')
    taints = ListField(NodeTaint, 'Taints')
