import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.devices.device_adapter import DeviceAdapter

# pylint: disable=too-many-instance-attributes


class Detection(SmartJsonClass):
    assigned_date = Field(str, 'Assigned Date')
    assigned_to = Field(str, 'Assigned To')
    c_score = Field(int, 'Certainty Score')
    category = Field(str, 'Category')
    certainty = Field(int, 'Certainty')
    custom_detection = Field(str, 'Custom Detection')
    description = Field(str, 'Description')
    detection = Field(str, 'Detection')
    detection_category = Field(str, 'Detection Category')
    detection_type = Field(str, 'Detection Type')
    detection_url = Field(str, 'Detection URL')
    first_timestamp = Field(datetime.datetime, 'First Timestamp')
    id = Field(int, 'ID')
    is_custom_model = Field(bool, 'Is Custom Model')
    is_marked_custom = Field(bool, 'Is Marked Custom')
    is_targeting_key_asset = Field(bool, 'Is Targeting Key Asset')
    last_timestamp = Field(datetime.datetime, 'Last Timestamp')
    note = Field(str, 'Mote')
    note_modified_by = Field(str, 'Note Modified By')
    note_modified_timestamp = Field(datetime.datetime, 'Note Modified Timestamp')
    src_account = Field(str, 'Source Account')
    src_ip = Field(str, 'Source IP')
    t_score = Field(int, 'Threat Score')
    tags = ListField(str, 'Tags')
    targets_key_asset = Field(bool, 'Targets Key Asset')
    threat = Field(int, 'Threat')
    triage_rule_id = Field(str, 'Triage Rule ID')
    url = Field(str, 'URL')


class VectraInstance(DeviceAdapter):
    active_traffic = Field(bool, 'Active Traffic')
    assigned_date = Field(datetime.datetime, 'Assigned Date')
    certainty_score = Field(int, 'Certainty score')
    detections_ids = ListField(str, 'Detections IDs')
    groups = ListField(str, 'Groups')
    host_luid = Field(str, 'Host LUID')
    host_session_luid = ListField(str, 'Host Session LUIDs')
    host_url = Field(str, 'Host URL')
    note = Field(str, 'Note')
    note_modified_by = Field(str, 'Note Modified By')
    note_modified_date = Field(datetime.datetime, 'Note Modified Date')
    sensor = Field(str, 'Sensor')
    sensor_name = Field(str, 'Sensor Name')
    state = Field(str, 'State')
    threat_score = Field(int, 'Threat Score')
    tags_list = ListField(str, 'Tags')
    url = Field(str, 'URL')
    previous_ips = ListField(str, 'Previous IPs')
    detections = ListField(Detection, 'Detections')
