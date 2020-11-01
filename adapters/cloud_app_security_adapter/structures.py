import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter


class EventServiceCount(SmartJsonClass):
    total = Field(int, 'Total Count')
    event = Field(str, 'Event')
    service = Field(str, 'Service')


# pylint: disable=too-many-instance-attributes
class SecurityLog(SmartJsonClass):
    service = Field(str, 'Service')
    event = Field(str, 'Event')
    scan_type = Field(str, 'Scan Type')
    affected_user = Field(str, 'Affected User')
    location = Field(str, 'Location')
    detection_time = Field(datetime.datetime, 'Detection Time')
    triggered_policy_name = Field(str, 'Triggered Policy Name')
    triggered_security_filter = Field(str, 'Triggered Security Filter')
    action = Field(str, 'Action')
    action_result = Field(str, 'Action Result')
    mail_message_id = Field(str, 'Mail Message ID')
    mail_message_sender = Field(str, 'Mail Message Sender')
    mail_message_recipient = ListField(str, 'Mail Message Recipient')
    mail_message_submit_time = Field(datetime.datetime, 'Mail Message Submit Time')
    mail_message_delivery_time = Field(datetime.datetime, 'Mail Message Delivery Time')
    mail_message_subject = Field(str, 'Mail Message Subject')
    mail_message_file_name = Field(str, 'Mail Message File Name')
    security_risk_name = Field(str, 'Security Risk Name')
    detected_by = Field(str, 'Detected_by')
    risk_level = Field(str, 'Risk Level')


class CloudAppSecurityUserInstance(UserAdapter):
    sender_event_count = Field(int, 'Events Count as Sender')
    recipient_event_count = Field(int, 'Events Count as Recipient')
    sender = ListField(SecurityLog, 'Sender Security Logs')
    recipient = ListField(SecurityLog, 'Recipient Security Logs')
    event_service_counts = ListField(EventServiceCount, 'Event Service Counts')
