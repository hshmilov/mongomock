from axonius.smart_json_class import SmartJsonClass
from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter


class Profile(SmartJsonClass):
    display_name_normalized = Field(str, 'Filtered Display Name')
    real_name = Field(str, 'Real Name')
    real_name_normalized = Field(str, 'Filtered Real Name')
    skype = Field(str, 'Skype')
    team = Field(str, 'Team')


class EnterpriseGridUser(SmartJsonClass):
    enterprise_id = Field(str, 'Enterprise Grid Organization ID')
    enterprise_name = Field(str, 'Enterprise Grid Organization Name')
    id = Field(str, 'Enterprise User ID')
    is_admin = Field(bool, 'Is Enterprise Admin')
    is_owner = Field(bool, 'Is Enterprise Owner')
    teams = ListField(str, 'Enterprise Team IDs')


class SlackUserInstance(UserAdapter):
    always_active = Field(bool, 'Always Active')
    color = Field(str, 'Username Color')
    deleted = Field(bool, 'Deleted')
    enterprise_user = Field(EnterpriseGridUser, 'Enterprise Grid')
    has_2fa = Field(bool, 'Has Two-Factor Authentication Enabled')
    is_app_user = Field(bool, 'Is Authorized')
    is_invited_user = Field(bool, 'Is Invited')
    is_owner = Field(bool, 'Is Owner')
    is_primary_owner = Field(bool, 'Is Primary Owner')
    is_restricted = Field(bool, 'Is Restricted')
    is_stranger = Field(bool, 'Belongs to Different Workspace')
    is_ultra_restricted = Field(bool, 'Is Ultra Restricted')
    locale = Field(str, 'Display Language')
    profile = Field(Profile, 'Profile')
    two_factor_type = Field(str, 'Two-Factor Authentication Type', enum=['app', 'sms'])
    user_time_zone = Field(str, 'Timezone')
    user_time_zone_label = Field(str, 'Timezome Name')
    user_time_zone_offset = Field(int, 'UTC Offset', description='Seconds')
    team_ids = ListField(str, 'Team IDs')
