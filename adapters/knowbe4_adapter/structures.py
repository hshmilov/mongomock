import datetime

from axonius.fields import Field, ListField
from axonius.smart_json_class import SmartJsonClass
from axonius.users.user_adapter import UserAdapter


class SecurityTestResult(SmartJsonClass):
    sec_test_name = Field(str, 'Test Name')
    sec_test_status = Field(str, 'Test Status')
    sec_test_started_at = Field(datetime.datetime, 'Test Start Time')
    sec_test_duration = Field(int, 'Test Duration')
    template_name = Field(str, 'Template Name')
    scheduled_at = Field(datetime.datetime, 'Scheduled At')
    delivered_at = Field(datetime.datetime, 'Delivered At')
    opened_at = Field(datetime.datetime, 'Opened At')
    clicked_at = Field(datetime.datetime, 'Clicked At')
    replied_at = Field(datetime.datetime, 'Replied At')
    attachment_opened_at = Field(datetime.datetime, 'Attachment Opened At')
    macro_enabled_at = Field(datetime.datetime, 'Macro Enabled At')
    data_entered_at = Field(datetime.datetime, 'Data Entered At')
    vulnerable_plugins_at = Field(datetime.datetime, 'Vulnerable Plugins At')
    exploited_at = Field(datetime.datetime, 'Exploited At')
    reported_at = Field(datetime.datetime, 'Reported At')
    bounced_at = Field(datetime.datetime, 'Bounced At')
    ip = Field(str, 'IP')
    ip_location = Field(str, 'IP Location')
    browser = Field(str, 'Browser')
    browser_version = Field(str, 'Browser Version')
    os = Field(str, 'OS')


class EnrollmentData(SmartJsonClass):
    content_type = Field(str, 'Content Type')
    module_name = Field(str, 'Module Name')
    campaign_name = Field(str, 'Campaign Name')
    enrollment_date = Field(datetime.datetime, 'Enrollment Date')
    start_date = Field(datetime.datetime, 'Start Date')
    completion_date = Field(datetime.datetime, 'Completion Date')
    status = Field(str, 'Status')
    time_spent = Field(int, 'Time Spent')
    policy_acknowledged = Field(bool, 'Policy Acknowledged')


class Knowbe4UserInstance(UserAdapter):
    archived_at = Field(datetime.datetime, 'Archived At')
    employee_start_date = Field(datetime.datetime, 'Employee Start Date')
    comment = Field(str, 'Comment')
    user_language = Field(str, 'Language')
    organization = Field(str, 'Organization')
    joined_on = Field(datetime.datetime, 'Joined On')
    aliases = ListField(str, 'Aliases')
    current_risk_score = Field(float, 'Current Risk Score')
    manager_email = Field(str, 'Manager Email')
    division = Field(str, 'Division')
    extension = Field(str, 'Extension')
    phish_prone_percentage = Field(float, 'Phish Prone Percentage')
    location = Field(str, 'Location')
    adi_manageable = Field(bool, 'ADI Manageable')
    sec_test_results = ListField(SecurityTestResult, 'Security Tests Results')
    enrollment_data = ListField(EnrollmentData, 'Enrollments')
