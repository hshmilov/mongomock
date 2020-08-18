import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


class RapidUserAccount(SmartJsonClass):
    name = Field(str, 'Name')
    full_name = Field(str, 'Full Name')


class RapidGroupAccount(SmartJsonClass):
    name = Field(str, 'Name')


# pylint: disable=too-many-instance-attributes
class RapidVulnerability(SmartJsonClass):
    vulnerability_id = Field(int, 'Vulnerability ID')
    nexpose_id = Field(str, 'Nexpose ID')
    title = Field(str, 'Title')
    date_published = Field(datetime.datetime, 'Date Published')
    date_added = Field(datetime.datetime, 'Date Added')
    date_modified = Field(datetime.datetime, 'Date Modified')
    severity_score = Field(int, 'Severity Score')
    severity = Field(str, 'Severity')
    critical = Field(int, 'Critical')
    severe = Field(int, 'Severe')
    moderate = Field(int, 'Moderate')
    pci_severity_score = Field(int, 'PCI Severity Score')
    pci_status = Field(str, 'PCI Status')
    pci_failures = Field(int, 'PCI Failures')
    risk_score = Field(float, 'Risk Score')
    cvss_vector = Field(str, 'CVSS Vector')
    cvss_score = Field(float, 'CVSS Score')
    pci_adjusted_cvss_score = Field(float, 'PCI Adjusted CVSS Score')
    denial_of_service = Field(bool, 'Denial Of Service')
    exploits = Field(int, 'Exploits')
    malware_kits = Field(int, 'Malware Kits')
    malware_popularity = Field(str, 'Malware Popularity')
    cvss_v3_vector = Field(str, 'CVSS V3 Vector')
    cvss_v3_score = Field(float, 'CVSS V3 Score')


class RapidTag(SmartJsonClass):
    id = Field(int, 'ID')
    name = Field(str, 'Name')
    type_ = Field(str, 'Type')
    source = Field(str, 'Source')
    created = Field(datetime.datetime, 'Created')
    risk_modifier = Field(float, 'Risk Modifier')
    color = Field(str, 'Color')


class RapidService(SmartJsonClass):
    id = Field(int, 'ID')
    service = Field(str, 'Service')
    port = Field(int, 'Port')
    protocol = Field(str, 'Protocol')
    vendor = Field(str, 'Vendor')
    family = Field(str, 'Family')
    name = Field(str, 'Name')
    version = Field(str, 'Version')
    certainty = Field(float, 'Certainty')
    credential_status = Field(str, 'Credential Status')


class RapidPolicy(SmartJsonClass):
    id = Field(int, 'ID')
    benchmark_id = Field(int, 'Benchmark ID')
    name = Field(str, 'Name')
    version = Field(str, 'Version')
    title = Field(str, 'Title')
    description = Field(str, 'Description')
    unscored_rules = Field(int, 'Unscored Rules')


class RapidAsset(SmartJsonClass):
    sites = ListField(str, 'Sites')
    credential_status = Field(str, 'Credential Status')
    risk_modifier = Field(float, 'Risk Modifier')
    last_assessed_vulnerabilities = Field(datetime.datetime, 'Last Assessed For Vulnerabilities')


class Rapid7NexposeWarehouseDeviceInstance(DeviceAdapter):
    rapid_asset = Field(RapidAsset, 'Asset')
    rapid_policies = ListField(RapidPolicy, 'Policies')
    rapid_services = ListField(RapidService, 'Rapid Services')
    rapid_tags = ListField(RapidTag, 'Tags')
    rapid_vulnerabilities = ListField(RapidVulnerability, 'Vulnerabilities')
    rapid_users = ListField(RapidUserAccount, 'Users Accounts')
    rapid_groups = ListField(RapidGroupAccount, 'Group Accounts')
