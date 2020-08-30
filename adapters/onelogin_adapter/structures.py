from datetime import datetime

from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter


class OneloginUserInstance(UserAdapter):
    activated_at = Field(datetime, 'Activated At')
    directory_id = Field(str, 'Directory ID')
    distinguished_name = Field(str, 'Distinguished Name')
    external_id = Field(str, 'External ID')
    group_id = Field(int, 'Group ID')
    invalid_login_attempts = Field(int, 'Invalid Login Attempts')
    invitation_sent_at = Field(datetime, 'Invitation Sent At')
    locked_until = Field(datetime, 'Locked Until')
    sam_account_name = Field(str, 'AD Login Name')
    state = Field(int, 'State')
    manager_user_id = Field(int, 'Manager ID')
    manager_ad_id = Field(int, 'Manager AD ID')
    comment = Field(str, 'Comment')
    company = Field(str, 'Company')
    preferred_locale_code = Field(str, 'Preferred Locale Code')
    role_ids = ListField(int, 'Role IDS')
    trusted_idp_id = Field(int, 'Trusted IDP ID')
    user_principal_name = Field(str, 'User Principal Name')
    locale_code = Field(str, 'Locale Code')
    openid_name = Field(str, 'OpenID Name')
    notes = Field(str, 'Notes')
