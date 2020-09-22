import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass


class IllumioDeviceTag(SmartJsonClass):
    href = Field(str, 'HREF')
    name = Field(str, 'Name')


class IllumioScope(SmartJsonClass):
    label = Field(str, 'Label')
    label_group = Field(str, 'Label Group')


class IllumioLabelResolver(SmartJsonClass):
    providers = ListField(str, 'Providers Workloads')
    consumers = ListField(str, 'Consumers Workloads')


class IllumioEndpoint(SmartJsonClass):
    actors = Field(str, 'Actors')
    label = Field(IllumioDeviceTag, 'Label')
    label_group = Field(IllumioDeviceTag, 'Label Group')
    workload = Field(IllumioDeviceTag, 'Workload')
    virtual_service = Field(IllumioDeviceTag, 'Virtual Service')
    virtual_server = Field(IllumioDeviceTag, 'Virtual Server')
    ip_list = Field(IllumioDeviceTag, 'IP List')  # appears to be a dict with a single attribute


class IllumioIpTablesStatement(SmartJsonClass):
    table_name = Field(str, 'Table Name')
    chain_name = Field(str, 'Chain Name')
    parameters = Field(str, 'Parameters')  # appears to be a dict with a single attribute


class IllumioIpTablesActor(SmartJsonClass):
    actors = Field(str, 'Actors')  # looks like a list, but the docs say str
    label = Field(IllumioDeviceTag, 'Label')
    label_group = Field(IllumioDeviceTag, 'Label Group')
    workload = Field(IllumioDeviceTag, 'Workload')


class IllumioIpTablesRule(SmartJsonClass):
    href = Field(str, 'HREF')
    enabled = Field(bool, 'Enabled')
    description = Field(str, 'Description')
    statements = ListField(IllumioIpTablesStatement, 'Statements')
    actors = ListField(IllumioIpTablesActor, 'Actors')
    ip_version = Field(str, 'IP Version', enum=['4', '6'])


class IllumioRule(SmartJsonClass):
    href = Field(str, 'HREF')
    enabled = Field(bool, 'Enabled')
    description = Field(str, 'Description')
    external_data_set = Field(str, 'External Data Set')
    external_data_reference = Field(str, 'External Data Reference')
    ingress_services = ListField(IllumioDeviceTag, 'Ingress Services')
    resolve_labels_as = Field(IllumioLabelResolver, 'Resolve Labels As')
    sec_connect = Field(bool, 'Secure Connection Established')
    stateless = Field(bool, 'Stateless Packet Filtering')
    machine_auth = Field(bool, 'Machine Authentication')
    providers = ListField(IllumioEndpoint, 'Providers')
    consumers = ListField(IllumioEndpoint, 'Consumers')
    consuming_security_principals = ListField(IllumioDeviceTag, 'Consuming Security Principals')
    unscoped_consumers = Field(bool, 'Unscoped Consumers')
    update_type = Field(str, 'Update Type')
    ip_tables_rules = ListField(IllumioIpTablesRule, 'IP Tables Rules')


class IllumioRuleset(SmartJsonClass):
    href = Field(str, 'HREF')
    created_at = Field(datetime.datetime, 'Created At')
    created_by = Field(str, 'Created By')  # this is pulled out of a dict.href
    updated_at = Field(datetime.datetime, 'Updated At')
    updated_by = Field(str, 'Updated By')  # this is pulled out of a dict.href
    deleted_at = Field(datetime.datetime, 'Deleted At')
    deleted_by = Field(str, 'Deleted By')
    update_type = Field(str, 'Update Type')
    name = Field(str, 'Name')
    description = Field(str, 'Description')
    external_dataset = Field(str, 'External Data Set')
    external_data_reference = Field(str, 'External Data Reference')
    enabled = Field(bool, 'Enabled')
    scopes = ListField(IllumioScope, 'Scopes')
    rules = ListField(IllumioRule, 'Rules')
    ip_tables_rules = ListField(IllumioIpTablesRule, 'IP Tables Rules')


class IllumioDeviceInterface(SmartJsonClass):
    name = Field(str, 'Interface Name')
    link_state = Field(str, 'Link State')
    address = Field(str, 'Address')
    cidr_block = Field(str, 'CIDR Block')  # docs say this is an int
    default_gateway_address = Field(str, 'Default Gateway Address')
    network = Field(IllumioDeviceTag, 'Network')
    network_detection_mode = Field(str, 'Network Detection Mode')
    friendly_name = Field(str, 'Friendly Name')


class IllumioDeviceLabel(SmartJsonClass):
    href = Field(str, 'HREF')
    name = Field(str, 'Name')
    key = Field(str, 'Key')
    value = Field(str, 'Value')


class IllumioDeviceWorkload(SmartJsonClass):
    href = Field(str, 'HREF')
    name = Field(str, 'Name')
    hostname = Field(str, 'Hostname')
    os_id = Field(str, 'OS ID')
    os_detail = Field(str, 'OS Detail')
    labels = ListField(IllumioDeviceLabel, 'Labels')
    public_ip = Field(str, 'Public IP')  # not adding to device
    interfaces = ListField(IllumioDeviceInterface, 'Interfaces')
    security_policy_applied_at = Field(datetime.datetime, 'Security Policy Applied')
    security_policy_received_at = Field(datetime.datetime, 'Security Policy Received')
    log_traffic = Field(bool, 'Log Traffic')
    mode = Field(str, 'Mode')
    visibility_level = Field(str, 'Visibility Level')
    online = Field(bool, 'Online')


class IllumioLatestEvent(SmartJsonClass):
    notification_type = Field(str, 'Notification Type')
    severity = Field(str, 'Severity')
    href = Field(str, 'HREF')
    info = Field(str, 'Info')
    timestamp = Field(datetime.datetime, 'Timestamp')


class IllumioDeviceCondition(SmartJsonClass):
    first_reported_timestamp = Field(datetime.datetime, 'First Reported')
    latest_event = Field(IllumioLatestEvent, 'Latest Event')


class IllumioDeviceInstance(DeviceAdapter):
    # ven schema
    href = Field(str, 'HREF')
    status = Field(str, 'Status')
    activation_type = Field(str, 'Activation Type')
    interfaces = ListField(IllumioDeviceInterface, 'Interfaces')
    workloads = ListField(IllumioDeviceWorkload, 'Workloads')
    container_cluster = Field(IllumioDeviceTag, 'Container Cluster')
    secure_connect = Field(str, 'Matching Issuer Name')
    last_goodbye_at = Field(datetime.datetime, 'Last Goodbye')
    created_by = Field(str, 'Created By (HREF)')
    updated_at = Field(datetime.datetime, 'Updated')
    updated_by = Field(str, 'Updated By (HREF)')
    conditions = ListField(IllumioDeviceCondition, 'Conditions')
    caps = ListField(str, 'Caps')
    rulesets = ListField(IllumioRuleset, 'Rulesets')
    # agent schema
    uptime_seconds = Field(int, 'Uptime in Seconds')
    online = Field(bool, 'Online')
    mode = Field(str, 'Mode')
    ip_tables_saved = Field(bool, 'IP Tables Saved')
    log_traffic = Field(bool, 'Log Traffic')
    # shared/common schema
    active_pce_fqdn = Field(str, 'Active PCE FQDN')
    target_pce_fqdn = Field(str, 'Target PCE FQDN')
    labels = ListField(IllumioDeviceLabel, 'Labels')
