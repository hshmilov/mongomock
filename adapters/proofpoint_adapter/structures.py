from axonius.fields import Field, ListField
from axonius.users.user_adapter import UserAdapter


class ProofpointUserInstance(UserAdapter):
    is_active = Field(bool, 'Active')
    alias_emails = ListField(str, 'Alias Mails')
    whitelist_senders = ListField(str, 'White List Senders')
    blacklist_senders = ListField(str, 'Black List Senders')
