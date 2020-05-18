from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass


class GCPServiceAccount(SmartJsonClass):
    """ This class supports GCP Service Account capture. """
    email = Field(str, 'Email')
    scopes = ListField(str, 'Scopes')


class AzureGCPIpConfiguration(SmartJsonClass):
    """ This class supports the collection of Azure IP Configuration data. """
    name = Field(str, 'Name')
    private_ip = Field(str, 'Private IP')
    public_ip = Field(str, 'Public IP')
    subnet = Field(str, 'Subnet')
    is_primary = Field(bool, 'Primary')
    app_sec_groups = ListField(str, 'Application Security Group')


class AzureGCPNetworkInterface(SmartJsonClass):
    """ This class supports the collection of Azure and GCP Network Interface data. """
    id = Field(str, 'Interface ID')
    name = Field(str, 'Name')
    type = Field(str, 'Type')
    public_ip = ListField(str, 'Public IP')
    private_ip = ListField(str, 'Private IP')
    ips = ListField(str, 'All IPs')
    sec_group_id = Field(str, 'Security Group ID')
    network_id = Field(str, 'Network ID')
    subnet_id = Field(str, 'Subnet ID')
    ip_configuration = ListField(AzureGCPIpConfiguration, 'IP Configuration')
    kind = Field(str, 'Kind')
    access_config = ListField(dict, 'Access Configuration')


class SecurityGroup(SmartJsonClass):
    """ A class for a Sophos-discovered AWS Security Groups. """
    key = Field(str, 'Security Group Name')
    value = Field(str, 'Security Group ID')
