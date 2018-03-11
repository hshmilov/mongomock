ADVANCED_COMPUTER_SEARCH_URL = 'advancedcomputersearches'
ADVANCED_COMPUTER_SEARCH = """<?xml version="1.0" encoding="UTF-8"?>
<advanced_computer_search>
    <name>{0}</name>
    <criteria>
        <size>1</size>
        <criterion>
            <name>Last Check-in</name>
            <and_or>and</and_or>
            <search_type>less than x days ago</search_type>
            <value>{1}</value>
            <opening_paren>false</opening_paren>
            <closing_paren>false</closing_paren>
        </criterion>
    </criteria>
    <display_fields>
        <size>88</size>
        <display_field>
            <name>Asset Tag</name>
        </display_field>
        <display_field>
            <name>Bar Code</name>
        </display_field>
        <display_field>
            <name>Bluetooth Low Energy Capability</name>
        </display_field>
        <display_field>
            <name>Computer Name</name>
        </display_field>
        <display_field>
            <name>Enrollment Method: PreStage enrollment</name>
        </display_field>
        <display_field>
            <name>IP Address</name>
        </display_field>
        <display_field>
            <name>iTunes Store Account</name>
        </display_field>
        <display_field>
            <name>JAMF Binary Version</name>
        </display_field>
        <display_field>
            <name>JSS Computer ID</name>
        </display_field>
        <display_field>
            <name>Last Check-in</name>
        </display_field>
        <display_field>
            <name>Last Enrollment</name>
        </display_field>
        <display_field>
            <name>Last iCloud Backup</name>
        </display_field>
        <display_field>
            <name>Last Inventory Update</name>
        </display_field>
        <display_field>
            <name>Last Reported IP Address</name>
        </display_field>
        <display_field>
            <name>Managed</name>
        </display_field>
        <display_field>
            <name>Managed By</name>
        </display_field>
        <display_field>
            <name>MDM Capability</name>
        </display_field>
        <display_field>
            <name>Platform</name>
        </display_field>
        <display_field>
            <name>UDID</name>
        </display_field>
        <display_field>
            <name>Architecture Type</name>
        </display_field>
        <display_field>
            <name>Available RAM Slots</name>
        </display_field>
        <display_field>
            <name>Battery Capacity</name>
        </display_field>
        <display_field>
            <name>Boot ROM</name>
        </display_field>
        <display_field>
            <name>Bus Speed MHz</name>
        </display_field>
        <display_field>
            <name>MAC Address</name>
        </display_field>
        <display_field>
            <name>Make</name>
        </display_field>
        <display_field>
            <name>Model</name>
        </display_field>
        <display_field>
            <name>Model Identifier</name>
        </display_field>
        <display_field>
            <name>NIC Speed</name>
        </display_field>
        <display_field>
            <name>Number of Processors</name>
        </display_field>
        <display_field>
            <name>Optical Drive</name>
        </display_field>
        <display_field>
            <name>Processor Speed MHz</name>
        </display_field>
        <display_field>
            <name>Processor Type</name>
        </display_field>
        <display_field>
            <name>Serial Number</name>
        </display_field>
        <display_field>
            <name>SMC Version</name>
        </display_field>
        <display_field>
            <name>Total Number of Cores</name>
        </display_field>
        <display_field>
            <name>Total RAM MB</name>
        </display_field>
        <display_field>
            <name>Active Directory Status</name>
        </display_field>
        <display_field>
            <name>FileVault Status</name>
        </display_field>
        <display_field>
            <name>Master Password Set</name>
        </display_field>
        <display_field>
            <name>Number of Available Updates</name>
        </display_field>
        <display_field>
            <name>Operating System</name>
        </display_field>
        <display_field>
            <name>Operating System Build</name>
        </display_field>
        <display_field>
            <name>Operating System Name</name>
        </display_field>
        <display_field>
            <name>Operating System Version</name>
        </display_field>
        <display_field>
            <name>Service Pack</name>
        </display_field>
        <display_field>
            <name>Gatekeeper</name>
        </display_field>
        <display_field>
            <name>System Integrity Protection</name>
        </display_field>
        <display_field>
            <name>XProtect Definitions Version</name>
        </display_field>
        <display_field>
            <name>Building</name>
        </display_field>
        <display_field>
            <name>Department</name>
        </display_field>
        <display_field>
            <name>Email Address</name>
        </display_field>
        <display_field>
            <name>Full Name</name>
        </display_field>
        <display_field>
            <name>Phone Number</name>
        </display_field>
        <display_field>
            <name>Position</name>
        </display_field>
        <display_field>
            <name>Room</name>
        </display_field>
        <display_field>
            <name>Username</name>
        </display_field>
        <display_field>
            <name>AppleCare ID</name>
        </display_field>
        <display_field>
            <name>Lease Expiration</name>
        </display_field>
        <display_field>
            <name>Life Expectancy</name>
        </display_field>
        <display_field>
            <name>PO Date</name>
        </display_field>
        <display_field>
            <name>PO Number</name>
        </display_field>
        <display_field>
            <name>Purchase Price</name>
        </display_field>
        <display_field>
            <name>Purchased or Leased</name>
        </display_field>
        <display_field>
            <name>Purchasing Account</name>
        </display_field>
        <display_field>
            <name>Purchasing Contact</name>
        </display_field>
        <display_field>
            <name>Vendor</name>
        </display_field>
        <display_field>
            <name>Warranty Expiration</name>
        </display_field>
        <display_field>
            <name>Boot Drive Available MB</name>
        </display_field>
        <display_field>
            <name>Boot Drive Percentage Full</name>
        </display_field>
        <display_field>
            <name>Core Storage Partition Scheme on Boot Partition</name>
        </display_field>
        <display_field>
            <name>Disk Encryption Configuration</name>
        </display_field>
        <display_field>
            <name>Drive Capacity MB</name>
        </display_field>
        <display_field>
            <name>FileVault 2 Eligibility</name>
        </display_field>
        <display_field>
            <name>FileVault 2 Individual Key Validation</name>
        </display_field>
        <display_field>
            <name>FileVault 2 Institutional Key</name>
        </display_field>
        <display_field>
            <name>FileVault 2 Recovery Key Type</name>
        </display_field>
        <display_field>
            <name>FileVault 2 Status</name>
        </display_field>
        <display_field>
            <name>Available SWUs</name>
        </display_field>
        <display_field>
            <name>Cached Packages</name>
        </display_field>
        <display_field>
            <name>Certificate Name</name>
        </display_field>
        <display_field>
            <name>Certificates Expiring</name>
        </display_field>
        <display_field>
            <name>Computer Group</name>
        </display_field>
        <display_field>
            <name>Licensed Software</name>
        </display_field>
        <display_field>
            <name>Local User Accounts</name>
        </display_field>
        <display_field>
            <name>Mapped Printers</name>
        </display_field>
        <display_field>
            <name>Packages Installed By Casper</name>
        </display_field>
        <display_field>
            <name>Running Services</name>
        </display_field>
    </display_fields>
</advanced_computer_search>"""
ADVANCED_COMPUTER_SEARCH_XML_NAME = 'advanced_computer_search'
ADVANCED_COMPUTER_SEARCH_DEVICE_LIST_NAME = 'computers'
COMPUTER_DEVICE_TYPE = 'computer'
COMPUTER_HISTORY_URL = 'computerhistory/id/'
COMPUTER_HISTORY_XML_NAME = 'computer_history'
COMPUTER_HISTORY_POLICY_LIST_NAME = 'policy_logs'
COMPUTER_HISTORY_POLICY_INFO_TYPE = 'policy_log'
ADVANCED_MOBILE_SEARCH_URL = 'advancedmobiledevicesearches'
ADVANCED_MOBILE_SEARCH = """<?xml version="1.0" encoding="UTF-8"?>
<advanced_mobile_device_search>
    <name>{0}</name>
    <criteria>
        <size>1</size>
        <criterion>
            <name>Last Inventory Update</name>
            <and_or>and</and_or>
            <search_type>less than x days ago</search_type>
            <value>{1}</value>
            <opening_paren>false</opening_paren>
            <closing_paren>false</closing_paren>
        </criterion>
    </criteria>
    <display_fields>
        <size>94</size>
        <display_field>
            <name>MEID</name>
        </display_field>
        <display_field>
            <name>ICCID</name>
        </display_field>
        <display_field>
            <name>IMEI</name>
        </display_field>
        <display_field>
            <name>Home Mobile Network Code</name>
        </display_field>
        <display_field>
            <name>Home Mobile Country Code</name>
        </display_field>
        <display_field>
            <name>Home Carrier Network</name>
        </display_field>
        <display_field>
            <name>Data Roaming Enabled</name>
        </display_field>
        <display_field>
            <name>Current Mobile Network Code</name>
        </display_field>
        <display_field>
            <name>Current Mobile Country Code</name>
        </display_field>
        <display_field>
            <name>Current Carrier Network</name>
        </display_field>
        <display_field>
            <name>Cellular Technology</name>
        </display_field>
        <display_field>
            <name>Carrier Settings Version</name>
        </display_field>
        <display_field>
            <name>Personal Device Profile Status</name>
        </display_field>
        <display_field>
            <name>Passcode Status</name>
        </display_field>
        <display_field>
            <name>Passcode Lock Grace Period Enforced (seconds)</name>
        </display_field>
        <display_field>
            <name>Passcode Compliance with Profile(s)</name>
        </display_field>
        <display_field>
            <name>Passcode Compliance</name>
        </display_field>
        <display_field>
            <name>Jailbreak Detected</name>
        </display_field>
        <display_field>
            <name>File Encryption Capability</name>
        </display_field>
        <display_field>
            <name>Hardware Encryption</name>
        </display_field>
        <display_field>
            <name>Data Protection</name>
        </display_field>
        <display_field>
            <name>Activation Lock Enabled</name>
        </display_field>
        <display_field>
            <name>Block Encryption Capability</name>
        </display_field>
        <display_field>
            <name>Warranty Expiration</name>
        </display_field>
        <display_field>
            <name>Vendor</name>
        </display_field>
        <display_field>
            <name>Purchasing Contact</name>
        </display_field>
        <display_field>
            <name>Purchasing Account</name>
        </display_field>
        <display_field>
            <name>Purchased or Leased</name>
        </display_field>
        <display_field>
            <name>Purchase Price</name>
        </display_field>
        <display_field>
            <name>PO Number</name>
        </display_field>
        <display_field>
            <name>PO Date</name>
        </display_field>
        <display_field>
            <name>Life Expectancy</name>
        </display_field>
        <display_field>
            <name>Lease Expiration</name>
        </display_field>
        <display_field>
            <name>AppleCare ID</name>
        </display_field>
        <display_field>
            <name>Username</name>
        </display_field>
        <display_field>
            <name>User Phone Number</name>
        </display_field>
        <display_field>
            <name>Room</name>
        </display_field>
        <display_field>
            <name>Position</name>
        </display_field>
        <display_field>
            <name>Full Name</name>
        </display_field>
        <display_field>
            <name>Email Address</name>
        </display_field>
        <display_field>
            <name>Department</name>
        </display_field>
        <display_field>
            <name>Building</name>
        </display_field>
        <display_field>
            <name>Used Space Percentage</name>
        </display_field>
        <display_field>
            <name>Wi-Fi MAC Address</name>
        </display_field>
        <display_field>
            <name>UDID</name>
        </display_field>
        <display_field>
            <name>Tethered</name>
        </display_field>
        <display_field>
            <name>Supervised</name>
        </display_field>
        <display_field>
            <name>Synced to Computer</name>
        </display_field>
        <display_field>
            <name>Shared iPad</name>
        </display_field>
        <display_field>
            <name>Serial Number</name>
        </display_field>
        <display_field>
            <name>Modem Firmware Version</name>
        </display_field>
        <display_field>
            <name>Model Number</name>
        </display_field>
        <display_field>
            <name>Model Identifier</name>
        </display_field>
        <display_field>
            <name>Model</name>
        </display_field>
        <display_field>
            <name>Managed</name>
        </display_field>
        <display_field>
            <name>Lost Mode Enabled</name>
        </display_field>
        <display_field>
            <name>Location Services for Self Service Mobile</name>
        </display_field>
        <display_field>
            <name>Locales</name>
        </display_field>
        <display_field>
            <name>Last Inventory Update</name>
        </display_field>
        <display_field>
            <name>Last iCloud Backup</name>
        </display_field>
        <display_field>
            <name>Last Enrollment</name>
        </display_field>
        <display_field>
            <name>Last Backup</name>
        </display_field>
        <display_field>
            <name>Languages</name>
        </display_field>
        <display_field>
            <name>JSS Mobile Device ID</name>
        </display_field>
        <display_field>
            <name>iTunes Store Account</name>
        </display_field>
        <display_field>
            <name>IP Address</name>
        </display_field>
        <display_field>
            <name>iOS Version</name>
        </display_field>
        <display_field>
            <name>iOS Build</name>
        </display_field>
        <display_field>
            <name>iCloud Backup Enabled</name>
        </display_field>
        <display_field>
            <name>Exchange Device ID</name>
        </display_field>
        <display_field>
            <name>Do Not Disturb Enabled</name>
        </display_field>
        <display_field>
            <name>Display Name</name>
        </display_field>
        <display_field>
            <name>Diagnostic and Usage Reporting Enabled</name>
        </display_field>
        <display_field>
            <name>Device Phone Number</name>
        </display_field>
        <display_field>
            <name>Device Ownership Type</name>
        </display_field>
        <display_field>
            <name>Device Locator Service Enabled</name>
        </display_field>
        <display_field>
            <name>Device ID</name>
        </display_field>
        <display_field>
            <name>Date Lost Mode Enabled</name>
        </display_field>
        <display_field>
            <name>Bluetooth MAC Address</name>
        </display_field>
        <display_field>
            <name>Capacity MB</name>
        </display_field>
        <display_field>
            <name>Bluetooth Low Energy Capability</name>
        </display_field>
        <display_field>
            <name>Battery Level</name>
        </display_field>
        <display_field>
            <name>Available Space MB</name>
        </display_field>
        <display_field>
            <name>Asset Tag</name>
        </display_field>
        <display_field>
            <name>App Analytics Enabled</name>
        </display_field>
        <display_field>
            <name>AirPlay Password</name>
        </display_field>
        <display_field>
            <name>Roaming</name>
        </display_field>
        <display_field>
            <name>Voice Roaming Enabled</name>
        </display_field>
        <display_field>
            <name>Applications</name>
        </display_field>
        <display_field>
            <name>Certificates</name>
        </display_field>
        <display_field>
            <name>Certificates Expiring</name>
        </display_field>
        <display_field>
            <name>Configuration Profiles</name>
        </display_field>
        <display_field>
            <name>Mobile Device Group</name>
        </display_field>
        <display_field>
            <name>Provisioning Profiles</name>
        </display_field>
    </display_fields>
</advanced_mobile_device_search>"""
ADVANCED_MOBILE_SEARCH_XML_NAME = 'advanced_mobile_device_search'
ADVANCED_MOBILE_SEARCH_DEVICE_LIST_NAME = 'mobile_devices'
MOBILE_DEVICE_TYPE = 'mobile_device'
ADVANCE_SEARCH_URL_NAME = "/name/{0}"

ADVANCE_SEARCH_NAME = "advanced_search_name"
USERNAME = 'username'
JAMF_DOMAIN = 'Jamf_Domain'
PASSWORD = 'password'
HTTP_PROXY = 'http_proxy'
HTTPS_PROXY = 'http_proxy'
CREATE_SEARCH_PRIVILEGES = 'create_search_privileges'
