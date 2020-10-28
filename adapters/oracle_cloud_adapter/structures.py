import datetime

from axonius.clients.oracle_cloud.consts import SecurityRuleOrigin
from axonius.clients.oracle_cloud.structures import OracleCloudAdapterEntity
from axonius.fields import Field, ListField, JsonStringFormat
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter
from axonius.users.user_adapter import UserAdapter
from axonius.utils.parsing import format_ip, format_ip_raw, format_mac


class OracleCloudUserCapabilities(SmartJsonClass):
    can_use_console_passwd = Field(bool, 'Can Use Console Password')
    can_use_api_keys = Field(bool, 'Can Use API Keys')
    can_use_auth_tokens = Field(bool, 'Can Use Auth Tokens')
    can_use_smtp_creds = Field(bool, 'Can Use SMTP Credentials')
    can_use_customer_secret_keys = Field(bool, 'Can Use Customer Secret Keys')
    can_use_oauth2_client_creds = Field(bool, 'Can Use OAuth2 Client Credentials')


class OracleCloudUserApiKey(SmartJsonClass):
    key_id = Field(str, 'Key ID')
    time_created = Field(datetime.datetime, 'Time Created')
    fingerprint = Field(str, 'Key Fingerprint')


class OracleCloudUserInstance(UserAdapter, OracleCloudAdapterEntity):
    oci_ocid = Field(str, 'User OCID')
    oci_compartment = Field(str, 'Oracle Cloud Infrastructure Compartment')
    is_email_verified = Field(bool, 'Email Verified')
    external_identifier = Field(str, 'External Identity ID')
    identity_provider_id = Field(str, 'Identity Provider ID')
    lifecycle_state = Field(str, 'Lifecycle State')
    is_mfa_active = Field(bool, 'MFA Activated')
    capabilities = Field(OracleCloudUserCapabilities, 'Capabilities')
    api_keys = ListField(OracleCloudUserApiKey, 'API Keys')


class OracleCloudVnic(SmartJsonClass):
    id = Field(str, 'VNIC ID')
    display_name = Field(str, 'Display Name')
    hostname_label = Field(str, 'Hostname Label')
    compartment_id = Field(str, 'Compartment ID')
    is_primary = Field(bool, 'Is Primary')
    lifecycle_state = Field(str, 'Lifecycle State')
    nsg_ids = ListField(str, 'Network Security Group OCIDs')
    subnet_id = Field(str, 'VCN Subnet OCID')
    vlan_id = Field(str, 'VCN VLAN OCID')
    time_created = Field(datetime.datetime, 'Time Created')
    mac_address = Field(str, 'MAC Address', converter=format_mac)
    private_ip = Field(str, 'Private IP', converter=format_ip, json_format=JsonStringFormat.ip)
    private_ip_raw = ListField(str, converter=format_ip_raw, hidden=True)
    public_ip = Field(str, 'Public IP', converter=format_ip, json_format=JsonStringFormat.ip)
    public_ip_raw = ListField(str, converter=format_ip_raw, hidden=True)


class OracleCloudPortRange(SmartJsonClass):
    min_port = Field(int, 'Minimum')
    max_port = Field(int, 'Maximum')


class OracleCloudNSGRule(SmartJsonClass):
    description = Field(str, 'Description')
    dest = Field(str, 'Destination')
    dest_type = Field(str, 'Destination Type')
    direction = Field(str, 'Direction')
    rule_id = Field(str, 'Security Rule ID')
    is_stateless = Field(bool, 'Is Stateless')
    is_valid = Field(bool, 'Is Valid')
    protocol = Field(str, 'Protocol')
    src = Field(str, 'Source')
    src_type = Field(str, 'Source Type')
    time_created = Field(datetime.datetime, 'Time Created')
    dst_port_range = Field(OracleCloudPortRange, 'Destination Port Range')
    src_port_range = Field(OracleCloudPortRange, 'Source Port Range')
    is_default = Field(bool, 'Rule in VCN Default Security List')
    sec_list_id = Field(str, 'Security List ID')
    vcn_id = Field(str, 'VCN ID')
    compartment_id = Field(str, 'Compartment ID')
    origin = Field(str, 'Rule Origin', enum=SecurityRuleOrigin.values())


class OracleCloudDeviceInstance(DeviceAdapter, OracleCloudAdapterEntity):
    oci_compartment = Field(str, 'Oracle Cloud Infrastructure Compartment')
    oci_region = Field(str, 'Oracle Cloud Infrastructure Region')
    time_created = Field(datetime.datetime, 'Time Created')
    tenancy = Field(str, 'Tenancy OCID')
    dedicated_vm_host_id = Field(str, 'Dedicated VM Host OCID')
    fault_domain = Field(str, 'Fault Domain Name')
    launch_mode = Field(str, 'VM Launch Mode')
    lifecycle_state = Field(str, 'Lifecycle State')
    instance_shape = Field(str, 'Instance Shape')
    availability_domain = Field(str, 'Availability Domain')
    maint_reboot_due = Field(datetime.datetime, 'Maintenance Reboot Due Time')
    vnics = ListField(OracleCloudVnic, 'VNICs')
    nsg_rules = ListField(OracleCloudNSGRule, 'Applied Network Security Rules',
                          description='Network Security Group (NSG) or Network Security List Security Rules '
                                      'that apply to this device')
    vcn_ids = ListField(str, 'VCN ID')
