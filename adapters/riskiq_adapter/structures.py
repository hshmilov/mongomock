import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter


class WebsiteComponent(SmartJsonClass):
    category = Field(str, 'Category')
    name = Field(str, 'Name')
    version = Field(str, 'Version')
    first_seen = Field(datetime.datetime, 'First Seen')
    last_seen = Field(datetime.datetime, 'Last Seen')
    affected = Field(bool, 'Affected by known CVE')
    rule_ids = ListField(str, 'Rule IDs')


class RiskIqOrganization(SmartJsonClass):
    workspace_id = Field(str, 'Workspace ID')
    workspace_org_id = Field(str, 'Workspace Organization ID')
    status = Field(str, 'Status')
    name = Field(str, 'Name')
    org_id = Field(str, 'Organization ID')
    created = Field(datetime.datetime, 'Created')
    updated = Field(datetime.datetime, 'Updated')


class RiskIqBrand(SmartJsonClass):
    workspace_id = Field(str, 'Workspace ID')
    workspace_brand_id = Field(str, 'Workspace Brand ID')
    status = Field(str, 'Status')
    name = Field(str, 'Name')
    brand_id = Field(str, 'Brand ID')
    created = Field(datetime.datetime, 'Created')
    updated = Field(datetime.datetime, 'Updated')


class RiskIqTag(SmartJsonClass):
    workspace_id = Field(str, 'Workspace ID')
    workspace_tag_id = Field(str, 'Workspace Tag ID')
    status = Field(str, 'Status')
    name = Field(str, 'Name')
    tag_id = Field(str, 'Tag ID')
    created = Field(datetime.datetime, 'Created')
    updated = Field(datetime.datetime, 'Updated')
    workspace_tag_type = Field(str, 'Workspace Tag Type')
    tag_color = Field(str, 'Tag Color')


class RiskIqDeviceInstance(DeviceAdapter):
    created_time = Field(datetime.datetime, 'Created at')
    updated_time = Field(datetime.datetime, 'Updated at')
    inventory_state = Field(str, 'Inventory State')
    external_id = Field(str, 'External ID')
    device_type = Field(str, 'Asset Type')
    is_auto_confirm = Field(bool, 'Auto Confirmed')
    is_enterprise = Field(bool, 'Enterprise')
    confidence = Field(str, 'Confidence')
    priority = Field(str, 'Priority')
    removed_state = Field(str, 'Removed State')
    riskiq_label = Field(str, 'RiskIQ Label')
    is_keystone = Field(bool, 'Keystone')
    external_metadata = Field(str, 'External Metadata')
    host = Field(str, 'Host')
    web_components = ListField(WebsiteComponent, 'Web Components')
    orgs = ListField(RiskIqOrganization, 'Organization Data')
    brands = ListField(RiskIqBrand, 'Brands')
    riskiq_tags = ListField(RiskIqTag, 'RiskIQ Tags')
    alexa_rank = Field(str, 'Alexa Rank')
