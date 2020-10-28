def get_default_cis_oracle_cloud_compliance_report() -> dict:
    return {'status': 'ok', 'rules': [
        {
            'account': '',
            'affected_entities': 0,
            'category': 'Identity and Access Management',
            'cis': '4.5 Use Multifactor Authentication For All Administrative Access\n'
                   'Use multi-factor authentication and encrypted channels for all '
                   'administrative account access.\n\n16.3 Require Multi-factor Authentication\n'
                   'Require multi-factor authentication for all user accounts, on all systems, '
                   'whether managed onsite or by a third-party provider.',
            'description': 'Multi-factor authentication is a method of authentication '
                           'that requires the use of more than one factor to verify a user’s identity.\n'
                           'With MFA enabled in the IAM service, when a user signs in to '
                           'Oracle Cloud Infrastructure, they are prompted for their user name '
                           'and password, which is the first factor (something that they know). '
                           'The user is then prompted to provide a second verification code from a '
                           'registered MFA device, which is the second factor (something that they have). '
                           'The two factors work together, requiring an extra layer of security to verify '
                           'the user’s identity and complete the sign-in process.\n'
                           'OCI IAM supports two-factor authentication using a password '
                           '(first factor) and a device that can generate a time-based one-time password '
                           '(TOTP) (second factor).\n'
                           'See [OCI documentation]'
                           '(https://docs.cloud.oracle.com/en-us/iaas/Content/Identity/Tasks/usingmfa.htm) '
                           'for more details. Multi factor authentication adds an extra layer of security '
                           'during the login process and makes it harder unauthorized users '
                           'to gain access to OCI resources.',
            'entities_results': '',
            'remediation': 'From Console:\n1. Login into OCI Console.\n2. Select \'Identity\' from '
                           'Services menu\n3. Select \'Users\' from Identity menu.\n4. '
                           'Click on an individual user.\n5. Ensure the word \'Enabled\' is next to '
                           '\'Multi-factor authentication\'.\n \nFrom CLI:\nSet up the OCI CLI with an '
                           'IAM administrator user who has access to read IAM policies.\n'
                           'Run OCI CLI command providing the root compartment OCID\n'
                           '\'\'\'\n'
                           'oci iam user list --query \'data[].[\"id\",\"name\",\"is-mfa-activated\"]'
                           '\' --output table\n\'\'\'\n'
                           'Verify that the table column named Column2 has not values of \'false\'',
            'results': {'checked': 0, 'failed': 0},
            'rule_name': 'Ensure MFA is enabled for all users with a console password',
            'section': '1.11',
            'status': 'Passed'
        },
        {
            'account': '',
            'affected_entities': 0,
            'category': 'Identity and Access Management',
            'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control',
            'description': 'API keys are used by administrators, developers, '
                           'services and scripts for accessing OCI APIs directly or via SDKs/OCI '
                           'CLI to search, create, update or delete OCI resources. \n'
                           'The API key is an RSA key pair. The private key is used for signing the '
                           'API requests and the public key is associated with a local or synchronized '
                           'user\'s profile. It is important to secure and rotate an API key every 90 '
                           'days or less as it provides the same level of access that a user it is '
                           'associated with has. \nIn addition to a security engineering best practice, '
                           'this is also a compliance requirement. For example, '
                           'PCI-DSS Section 3.6.4 states, \"Verify that key-management procedures '
                           'include a defined cryptoperiod for each key type in use and define a '
                           'process for key changes at the end of the defined crypto period(s).\"',
            'entities_results': '',
            'remediation': 'OCI Native IAM\nFrom Console:\n1. Login to OCI Console.\n'
                           '2. Select \'Identity\' from the Services menu.\n'
                           '3. Select \'Users\' from the Identity menu.\n'
                           '4. Click on an individual user under the Name heading.\n'
                           '5. Click on \'API Keys\' in the lower left hand corner of the page.\n'
                           '6. Ensure the date of the API key under the \'Created\' column of the API '
                           'Key is no more than 90 days old.\n \nFrom CLI:\n'
                           '\'\'\'\n'
                           'oci iam user api-key list --user-id <user_ocid> --query data[*].'
                           '[\\\"time-created\\\",\\\"fingerprint\\\"]\n\'\'\'',
            'results': {'checked': 0, 'failed': 0},
            'rule_name': 'Ensure user API keys rotate within 90 days or less',
            'section': '1.12',
            'status': 'Passed'
        },
        {
            'account': '',
            'affected_entities': 0,
            'category': 'Identity and Access Management',
            'cis': '4 Controlled Use of Administrative Privileges\n'
                   'Controlled Use of Administrative Privileges\n\n'
                   '16 Account Monitoring and Control\nAccount Monitoring and Control',
            'description': 'Tenancy administrator users have full access to the organization\'s '
                           'OCI tenancy. API keys associated with user accounts are used for invoking '
                           'the OCI APIs via custom programs or clients like CLI/SDKs. '
                           'The clients are typically used for performing day-to-day operations and '
                           'should never require full tenancy access. Service-level administrative '
                           'users with API keys should be used instead. For performing day-to-day '
                           'operations tenancy administrator access is not needed.\n'
                           'Service-level administrative users with API keys should be used '
                           'to apply privileged security principle.',
            'entities_results': '',
            'remediation': 'OCI Native IAM\n'
                           'From Console: \n'
                           '1. Login to OCI Console.\n'
                           '2. Verify user profile of each user who is member of the \'Administrators\' '
                           'group directly or via federation group mapping.\n'
                           '3. Go to \'Identity\'-> \'Users\' and click on each local or synchronized '
                           '\'Administrators\' member profile\n'
                           '4. Click on API Keys to verify if a user has an API key associated.',
            'results': {'checked': 0, 'failed': 0},
            'rule_name': 'Ensure API keys are not created for tenancy administrator users',
            'section': '1.13',
            'status': 'Passed'
        },
        {
            'account': '',
            'affected_entities': 0,
            'category': 'Networking',
            'cis': '9.2 Ensure Only Approved Ports, Protocols and Services Are Running\n'
                   'Ensure that only network ports, protocols, and services listening '
                   'on a system with validated business needs, are running on each system.',
            'description': 'Security lists provide stateful or stateless filtering of '
                           'ingress/egress network traffic to OCI resources on a subnet level. '
                           'It is recommended that no security group allows unrestricted ingress '
                           'access to port 22. Removing unfettered connectivity to remote console '
                           'services, such as Secure Shell (SSH), reduces a server\'s exposure to risk.',
            'entities_results': '',
            'remediation': 'From Console:\n1. Login into the OCI Console\n'
                           '2. Click in the search bar, top of the screen.\n'
                           '3. Type \'Advanced Resource Query\' and hit \'enter\'.\n'
                           '4. Click the \'Advanced Resource Query\' button in the upper '
                           'right of the screen.\n5. Enter the following query in the query box:\n'
                           '\'\'\'\n'
                           'query SecurityList resources where \n'
                           '(IngressSecurityRules.source = \'0.0.0.0/0\' && \n'
                           'IngressSecurityRules.protocol = 6 && IngressSecurityRules.tcpOptions.'
                           'destinationPortRange.max = 22 && IngressSecurityRules.tcpOptions.'
                           'destinationPortRange.min = 22) \n'
                           '\'\'\'\n'
                           '6. Ensure query returns no results.\n\n'
                           'From CLI:\n'
                           '1. Execute the following command\n'
                           '\'\'\'\n'
                           'oci search resource structured-search --query-text '
                           '\"query SecurityList resources where \n'
                           '(IngressSecurityRules.source = \'0.0.0.0/0\' && \n'
                           'IngressSecurityRules.protocol = 6 && IngressSecurityRules.tcpOptions.'
                           'destinationPortRange.max = 22 && IngressSecurityRules.tcpOptions.'
                           'destinationPortRange.min = 22) \n\"\n'
                           '\'\'\'\n'
                           '2. Ensure query returns no results.',
            'results': {'checked': 0, 'failed': 0},
            'rule_name': 'Ensure no security lists allow ingress from 0.0.0.0/0 to port 22',
            'section': '2.1',
            'status': 'Passed'
        },
        {
            'account': '',
            'affected_entities': 0,
            'category': 'Networking',
            'cis': '9.2 Ensure Only Approved Ports, Protocols and Services Are Running\n'
                   'Ensure that only network ports, protocols, and services listening '
                   'on a system with validated business needs, are running on each system.',
            'description': 'Security lists provide stateful or stateless filtering of '
                           'ingress/egress network traffic to OCI resources on a subnet level. '
                           'It is recommended that no security group allows unrestricted ingress '
                           'access to port 3389. Removing unfettered connectivity to remote console '
                           'services, such as Remote Desktop Protocol (RDP), reduces a server\'s exposure to risk.',
            'entities_results': '',
            'remediation': 'From Console:\n1. Login into the OCI Console\n'
                           '2. Click in the search bar, top of the screen.\n'
                           '3. Type \'Advanced Resource Query\' and hit \'enter\'.\n'
                           '4. Click the \'Advanced Resource Query\' button in the upper '
                           'right of the screen.\n5. Enter the following query in the query box:\n'
                           '\'\'\'\n'
                           'query SecurityList resources where \n'
                           '(IngressSecurityRules.source = \'0.0.0.0/0\' && \n'
                           'IngressSecurityRules.protocol = 6 && IngressSecurityRules.tcpOptions.'
                           'destinationPortRange.max = 3389 && IngressSecurityRules.tcpOptions.'
                           'destinationPortRange.min = 3389) \n'
                           '\'\'\'\n'
                           '6. Ensure query returns no results.\n\n'
                           'From CLI:\n'
                           '1. Execute the following command\n'
                           '\'\'\'\n'
                           'oci search resource structured-search --query-text '
                           '\"query SecurityList resources where \n'
                           '(IngressSecurityRules.source = \'0.0.0.0/0\' && \n'
                           'IngressSecurityRules.protocol = 6 && IngressSecurityRules.tcpOptions.'
                           'destinationPortRange.max = 3389 && IngressSecurityRules.tcpOptions.'
                           'destinationPortRange.min = 3389) \n\"\n'
                           '\'\'\'\n'
                           '2. Ensure query returns no results.',
            'results': {'checked': 0, 'failed': 0},
            'rule_name': 'Ensure no security lists allow ingress from 0.0.0.0/0 to port 3389',
            'section': '2.2',
            'status': 'Passed'
        },
        {
            'account': '',
            'affected_entities': 0,
            'category': 'Networking',
            'cis': '9.2 Ensure Only Approved Ports, Protocols and Services Are Running\n'
                   'Ensure that only network ports, protocols, and services listening '
                   'on a system with validated business needs, are running on each system.',
            'description': 'A default security list is created when a Virtual Cloud Network (VCN) is created. '
                           'Security lists provide stateful filtering of ingress and egress network traffic to '
                           'OCI resources. It is recommended no security list allows unrestricted ingress access '
                           'to Secure Shell (SSH) via port 22. Removing unfettered connectivity to remote console '
                           'services, such as SSH on port 22, reduces a server\'s exposure to unauthorized access.',
            'entities_results': '',
            'remediation': 'From Console:\n'
                           '1. Login into the OCI Console\n'
                           '2. Click on \'Networking -> Virtual Cloud Networks\'\n'
                           '3. For each VCN listed \'Click on Security Lists\'\n'
                           '4. Click on \'Default Security List for <VCN Name>\'\n'
                           '5. Verify that there is no Ingress rule with '
                           '\'Source 0.0.0.0/0, IP Protocol 22 and Destination Port Range 22\'',
            'results': {'checked': 0, 'failed': 0},
            'rule_name': 'Ensure the default security list of every VCN restricts all traffic except ICMP',
            'section': '2.5',
            'status': 'Passed'
        },
        {
            'account': '',
            'affected_entities': 0,
            'category': 'Logging and Monitoring',
            'cis': '6 Maintenance, Monitoring and Analysis of Audit Logs\n'
                   'Maintenance, Monitoring and Analysis of Audit Logs',
            'description': 'Ensuring audit logs are kept for 365 days. '
                           'Log retention controls how long activity logs should be retained. '
                           'Studies have shown that The Mean Time to Detect(MTTD) a cyber breach is '
                           'anywhere from 30 days in some sectors to up to 206 days in others. '
                           'Retaining logs for at least 365 days or more will provide the '
                           'ability to respond to incidents.',
            'entities_results': '',
            'remediation': 'From Console:\n'
                           '1. Go to the Tenancy Details page: '
                           '[https://console.us-ashburn-1.oraclecloud.com/a/tenancy]'
                           '(https://console.us-ashburn-1.oraclecloud.com/a/tenancy)\n'
                           '2. View the \'Audit Retention Period\' and ensure it is set to 365 Days.\n \n'
                           'From CLI:\n1. Retrieve the audit retention period from the command line\n'
                           '\'\'\'\noci audit config get --compartment-id <compartment OCID>\n'
                           '\'\'\'\n'
                           '2. Ensure the returned JSON contains \'retention-period-days\' of 365.',
            'results': {'checked': 0, 'failed': 0},
            'rule_name': 'Ensure audit log retention period is set to 365 days',
            'section': '3.1',
            'status': 'Passed'
        },
    ]}
