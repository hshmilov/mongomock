from axonius.fields import ListField, Field
import datetime


# UserAccountControl flags
# https://support.microsoft.com/en-us/help/305144/how-to-use-the-useraccountcontrol-flags-to-manipulate-user-account-pro
SCRIPT = 0x0001
ACCOUNTDISABLE = 0x0002
HOMEDIR_REQUIRED = 0x0008
LOCKOUT = 0x0010
PASSWD_NOTREQD = 0x0020
PASSWD_CANT_CHANGE = 0x0040
ENCRYPTED_TEXT_PWD_ALLOWED = 0x0080
TEMP_DUPLICATE_ACCOUNT = 0x0100
NORMAL_ACCOUNT = 0x0200
INTERDOMAIN_TRUST_ACCOUNT = 0x0800
WORKSTATION_TRUST_ACCOUNT = 0x1000
SERVER_TRUST_ACCOUNT = 0x2000
DONT_EXPIRE_PASSWORD = 0x10000
MNS_LOGON_ACCOUNT = 0x20000
SMARTCARD_REQUIRED = 0x40000
TRUSTED_FOR_DELEGATION = 0x80000
NOT_DELEGATED = 0x100000
USE_DES_KEY_ONLY = 0x200000
DONT_REQ_PREAUTH = 0x400000
PASSWORD_EXPIRED = 0x800000
TRUSTED_TO_AUTH_FOR_DELEGATION = 0x1000000
PARTIAL_SECRETS_ACCOUNT = 0x04000000

AD_OBJECT_TYPE_ENUM = ["Typical User", "Domain Controller", "Workstation/Server"]
AD_OBJECT_DIALIN_OPTIONS = ["Dial In Enabled", "Dial In Disabled", "Control Access Through NPS Network Policy"]
AD_DELEGATION_POLICY = ["Do Not Trust For Delegation",
                        "Trust For Delegation To Any Service",
                        "Trust For Delegation To Specified Services"]

EXCHANGE_SERVER_ROLES_ENUM = ["Mailbox", "CAS", "Unified Messaging", "Hub Transport", "Edge Transport"]

EXCHANGE_SERVER_MAILBOX_ROLE = 0x2
EXCHANGE_SERVER_CAS_ROLE = 0x4
EXCHANGE_SERVER_UNIFIED_MESSAGING_ROLE = 0x10
EXCHANGE_SERVER_HUB_TRANSPORT_ROLE = 0x20
EXCHANGE_SERVER_EDGE_TRANSPORT_ROLE = 0x40


class ADEntity(object):
    ad_sid = Field(str, "AD objectSid")
    ad_guid = Field(str, "AD objectGUID")
    ad_name = Field(str, "AD name")
    ad_sAMAccountName = Field(str, "AD sAMAccountName")
    ad_distinguished_name = Field(str, "AD distinguishedName")
    ad_account_expires = Field(datetime.datetime, "AD accountExpires")
    ad_object_class = ListField(str, "AD objectClass")
    ad_object_category = Field(str, "AD objectCategory")
    ad_organizational_unit = ListField(str, "AD Organizational Unit")
    ad_last_logoff = Field(datetime.datetime, "AD lastLogoff")
    ad_last_logon = Field(datetime.datetime, "AD lastLogon")
    ad_last_logon_timestamp = Field(datetime.datetime, 'AD lastLogonTimestamp')
    ad_bad_password_time = Field(datetime.datetime, 'AD badPasswordTime')
    ad_bad_pwd_count = Field(int, "AD badPwdCount")
    ad_managed_by = Field(str, "AD managedBy")
    ad_password_last_set = Field(datetime.datetime, 'AD pwdLastSet')
    ad_cn = Field(str, "AD Common Name (CN)")
    ad_member_of = ListField(str, "AD memberOf")
    ad_usn_changed = Field(int, "AD uSNChanged")
    ad_usn_created = Field(int, "AD uSNCreated")
    ad_when_changed = Field(datetime.datetime, "AD whenChanged")
    ad_when_created = Field(datetime.datetime, "AD whenCreated")
    ad_is_critical_system_object = Field(bool, "AD isCriticalSystemObject")
    ad_dialin_policy = Field(str, "AD Dial In Policy", enum=AD_OBJECT_DIALIN_OPTIONS)
    ad_msds_allowed_to_delegate_to = ListField(str, "AD msDS-AllowedToDelegateTo")
    ad_delegation_policy = Field(str, "AD Delegation Policy", enum=AD_DELEGATION_POLICY)
    ad_pwd_must_change = Field(bool, "AD Password Must Change")

    # User Account Control
    ad_uac_logon_script = Field(bool, "AD logon script will be run (SCRIPT)")
    ad_uac_account_disable = Field(bool, "AD Account Disabled")
    ad_uac_homedir_required = Field(bool, "AD Home Folder Required")
    ad_uac_password_not_required = Field(bool, "AD Password Not Required")
    ad_uac_password_cant_change = Field(bool, "AD Password Can't Change")
    ad_uac_encrypted_text_password_allowed = Field(bool, "AD Encrypted Text Password Allowed (Reversible Password)")
    ad_uac_temp_duplicate_account = Field(bool, "AD Temp Duplicate Account")
    ad_uac_normal_account = Field(bool, "AD Normal Account")
    ad_uac_interdomain_trust_account = Field(bool, "AD Interdomain Trust Account")
    ad_uac_workstation_trust_account = Field(bool, "AD Workstation Trust Account")
    ad_uac_server_trust_account = Field(bool, "AD Server Trust Account")
    ad_uac_dont_expire_password = Field(bool, "AD Password Never Expires")
    ad_uac_mns_logon_account = Field(bool, "AD MNS Logon Account")
    ad_uac_smartcard_required = Field(bool, "AD Smart Card Required")
    ad_uac_trusted_for_delegation = Field(bool, "AD Account Trusted For Delegation")
    ad_uac_not_delegated = Field(bool, "AD Account Not Delegated")
    ad_uac_use_des_key_only = Field(bool, "AD Use DES Key Only")
    ad_uac_dont_require_preauth = Field(bool, "AD No Pre Authentication Required")
    ad_uac_password_expired = Field(bool, "AD Password Has Expired")
    ad_uac_trusted_to_auth_for_delegation = Field(bool, "AD Account Trusted To Authenticate For Delegation")
    ad_uac_partial_secrets_account = Field(bool, "AD Partial Secret Account (Read Only Domain Controller)")

    # Our own parsed things
    ad_object_type = Field(str, "Object Type", enum=AD_OBJECT_TYPE_ENUM)

    # Special parsed vars
    ad_site_name = Field(str, "AD Site Name")
    ad_site_location = Field(str, "AD Site Location")
    ad_subnet = Field(str, "AD Subnet")

    # Values only for DC's
    ad_is_dc = Field(bool, "AD Is Domain Controller (DC)")
    ad_dc_gc = Field(bool, "AD DC Global Catalog")
    ad_dc_infra_master = Field(bool, "AD DC Infrastructure Master")
    ad_dc_rid_master = Field(bool, "AD DC RID Master")
    ad_dc_pdc_emulator = Field(bool, "AD DC PDC Emulator")
    ad_dc_naming_master = Field(bool, "AD Naming Master")
    ad_dc_schema_master = Field(bool, "AD Schema Master")
    ad_dc_is_dhcp_server = Field(bool, "AD DHCP Server")
    ad_dc_is_nps_server = Field(bool, "AD NPS Server")

    # Values only for exhange server
    ad_is_exchange_server = Field(bool, "AD Exchange Server")
    ad_exchange_server_organization = Field(str, "AD Exchange Server Organization")
    ad_exchange_server_admin_group = Field(str, "AD Exchange Server Admin Group")
    ad_exchange_server_name = Field(str, "AD Exchange Server Name")
    ad_exchange_server_roles = ListField(str, "AD Exchange Server Roles")
    ad_exchange_server_serial = Field(str, "AD Exchange Server Serial")
    ad_exchange_server_product_id = Field(str, "AD Exchange Server Product ID")

    def figure_out_exchange_server_roles(self, exchange_server_roles):
        assert type(exchange_server_roles) == int

        roles = []
        if exchange_server_roles & EXCHANGE_SERVER_MAILBOX_ROLE > 0:
            roles.append(EXCHANGE_SERVER_ROLES_ENUM[0])

        if exchange_server_roles & EXCHANGE_SERVER_CAS_ROLE > 0:
            roles.append(EXCHANGE_SERVER_ROLES_ENUM[1])

        if exchange_server_roles & EXCHANGE_SERVER_UNIFIED_MESSAGING_ROLE > 0:
            roles.append(EXCHANGE_SERVER_ROLES_ENUM[2])

        if exchange_server_roles & EXCHANGE_SERVER_HUB_TRANSPORT_ROLE > 0:
            roles.append(EXCHANGE_SERVER_ROLES_ENUM[3])

        if exchange_server_roles & EXCHANGE_SERVER_EDGE_TRANSPORT_ROLE > 0:
            roles.append(EXCHANGE_SERVER_ROLES_ENUM[4])

        self.ad_exchange_server_roles = roles

    def figure_out_dial_in_policy(self, msNPAllowDialin):
        if msNPAllowDialin is None:
            self.ad_dialin_policy = AD_OBJECT_DIALIN_OPTIONS[2]
        elif msNPAllowDialin is True:
            self.ad_dialin_policy = AD_OBJECT_DIALIN_OPTIONS[0]
        elif msNPAllowDialin is False:
            self.ad_dialin_policy = AD_OBJECT_DIALIN_OPTIONS[1]

    def figure_out_delegation_policy(self, user_account_control, msds_allowed_to_delegate_to):
        if msds_allowed_to_delegate_to is not None:
            self.ad_delegation_policy = AD_DELEGATION_POLICY[2]
        else:
            if user_account_control & TRUSTED_FOR_DELEGATION > 0:
                self.ad_delegation_policy = AD_DELEGATION_POLICY[1]
            else:
                self.ad_delegation_policy = AD_DELEGATION_POLICY[0]

    def parse_user_account_control(self, user_account_control):
        if user_account_control is not None and type(user_account_control) == int:
            self.ad_uac_logon_script = bool(user_account_control & SCRIPT)
            self.ad_uac_homedir_required = bool(user_account_control & HOMEDIR_REQUIRED)
            self.ad_uac_account_disable = bool(user_account_control & ACCOUNTDISABLE)
            self.ad_uac_password_not_required = bool(user_account_control & PASSWD_NOTREQD)
            self.ad_uac_password_cant_change = bool(user_account_control & PASSWD_CANT_CHANGE)
            self.ad_uac_encrypted_text_password_allowed = bool(user_account_control & ENCRYPTED_TEXT_PWD_ALLOWED)
            self.ad_uac_temp_duplicate_account = bool(user_account_control & TEMP_DUPLICATE_ACCOUNT)
            self.ad_uac_normal_account = bool(user_account_control & NORMAL_ACCOUNT)
            self.ad_uac_interdomain_trust_account = bool(user_account_control & INTERDOMAIN_TRUST_ACCOUNT)
            self.ad_uac_workstation_trust_account = bool(user_account_control & WORKSTATION_TRUST_ACCOUNT)
            self.ad_uac_server_trust_account = bool(user_account_control & SERVER_TRUST_ACCOUNT)
            self.ad_uac_dont_expire_password = bool(user_account_control & DONT_EXPIRE_PASSWORD)
            self.ad_uac_mns_logon_account = bool(user_account_control & MNS_LOGON_ACCOUNT)
            self.ad_uac_smartcard_required = bool(user_account_control & SMARTCARD_REQUIRED)
            self.ad_uac_trusted_for_delegation = bool(user_account_control & TRUSTED_FOR_DELEGATION)
            self.ad_uac_not_delegated = bool(user_account_control & NOT_DELEGATED)
            self.ad_uac_use_des_key_only = bool(user_account_control & USE_DES_KEY_ONLY)
            self.ad_uac_dont_require_preauth = bool(user_account_control & DONT_REQ_PREAUTH)
            self.ad_uac_password_expired = bool(user_account_control & PASSWORD_EXPIRED)
            self.ad_uac_trusted_to_auth_for_delegation = bool(user_account_control & TRUSTED_TO_AUTH_FOR_DELEGATION)
            self.ad_uac_partial_secrets_account = bool(user_account_control & PARTIAL_SECRETS_ACCOUNT)

            # From Microsoft link on UserAccountControl:
            # These are the default UserAccountControl values for the certain objects:
            # Typical user : 0x200 (512)
            # Domain controller : 0x82000 (532480)
            # Workstation/server: 0x1000 (4096)

            if user_account_control == NORMAL_ACCOUNT:
                # That is just a typical user
                self.ad_object_type = AD_OBJECT_TYPE_ENUM[0]
            elif user_account_control == (TRUSTED_FOR_DELEGATION | SERVER_TRUST_ACCOUNT):
                # That is a DC
                self.ad_object_type = AD_OBJECT_TYPE_ENUM[1]
            elif user_account_control == WORKSTATION_TRUST_ACCOUNT:
                # That is just a computer
                self.ad_object_type = AD_OBJECT_TYPE_ENUM[2]
