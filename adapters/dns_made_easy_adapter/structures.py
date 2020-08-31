import datetime

from axonius.devices.device_adapter import DeviceAdapter
from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass


class DnsMadeEasyNameServer(SmartJsonClass):
    ipv6 = Field(str, 'IPv6')
    ipv4 = Field(str, 'IPv4')
    fqdn = Field(str, 'FQDN')
    gtd_location_id = Field(int, 'GTD Location ID')
    group_id = Field(int, 'Group ID')
    id = Field(int, 'ID')


class DnsMadeEasyDomain(SmartJsonClass):
    dnsme_id = Field(int, 'ID')
    dnsme_name = Field(str, 'Name')
    created = Field(datetime.datetime, 'Created')
    folder_id = Field(int, 'Folder ID')
    gtd_enabled = Field(bool, 'Global Traffic Directory Enabled')
    updated = Field(datetime.datetime, 'Updated')
    process_multi = Field(bool, 'Process Multi')
    active_third_parties = ListField(str, 'Active 3rd Parties')
    pending_action_id = Field(int, 'Pending Action ID')
    delegate_nameservers = ListField(DnsMadeEasyNameServer, 'Delegate Nameservers')
    nameservers = ListField(DnsMadeEasyNameServer, 'Nameservers')
    vanity_id = Field(int, 'Vanity ID')
    # this is not listed in the docs, but is in sample responses
    vanity_nameservers = ListField(DnsMadeEasyNameServer, 'Vanity Nameservers')
    # following are listed in the docs, but not in any sample responses
    soa_id = Field(int, 'SOA Record ID')
    template_id = Field(int, 'Template ID')
    transfer_acl_id = Field(int, 'Applied Transfer ACL ID')
    axfr_servers = ListField(str, 'Applied AXFR ACL Servers')


# This "device" is a domain record describing a subdomain
class DnsMadeEasyDeviceInstance(DeviceAdapter):
    subdomain_name = Field(str, 'Name')
    ip_alias_or_server = Field(str, 'Value')
    record_type = Field(str, 'Record Type')
    record_id = Field(int, 'Record ID')
    source = Field(str, 'Source')
    ttl = Field(int, 'TTL')
    gtd_location = Field(str, 'Global Traffic Director Location')
    source_id = Field(int, 'Source ID')
    failover = Field(bool, 'Failover')
    failed = Field(bool, 'Failed')
    monitor = Field(bool, 'Monitor')
    hard_link = Field(bool, 'Hard Link')
    dynamic_dns = Field(bool, 'Dynamic DNS')
    # following are listed in the docs, but not in any sample responses
    keywords = Field(str, 'Keywords')
    title = Field(str, 'Title')
    redirect_type = Field(str, 'Redirect Type')
    mx_level = Field(int, 'MX Level')
    srv_weight = Field(int, 'SRV Weight')
    srv_priority = Field(int, 'SRV Priority')
    srv_port = Field(int, 'SRV Port')
    dnsme_domain = Field(DnsMadeEasyDomain, 'DNS Made Easy Domain')
    dnsme_domain_name = Field(str, 'DNS Made Easy Domain Name')
