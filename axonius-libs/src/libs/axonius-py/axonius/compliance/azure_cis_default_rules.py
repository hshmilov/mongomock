def get_default_cis_azure_compliance_report():
    return {'rules': [{'account': '',
                       'affected_entities': 0,
                       'category': 'Identity and Access Management',
                       'cis': '16.8 Disable Any Unassociated Accounts\n'
                              'Disable any account that cannot be associated with a '
                              'business process or business owner.',
                       'description': 'Do not add guest users if not needed. Azure AD is '
                                      'extended to include Azure AD B2B '
                                      'collaboration,allowing you to invite people from '
                                      'outside your organization to be guest users in '
                                      'your cloud account.Until you have a business need '
                                      'to provide guest access to any user, avoid '
                                      'creating guest users.Guest users are typically '
                                      'added outside your employee '
                                      'on-boarding/off-boarding process and could '
                                      'potentially be overlooked indefinitely leading to '
                                      'a potential vulnerability.',
                       'entities_results': '',
                       'remediation': 'Delete the "Guest" users.',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that there are no guest users',
                       'section': '1.3',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Identity and Access Management',
                       'cis': '4 Controlled Use of Administrative\n'
                              'Privileges  Controlled Use of Administrative Privileges \n'
                              '16 Account Monitoring and Control\n'
                              'Account Monitoring and Control',
                       'description': 'Subscription ownership should not include '
                                      'permission to create custom owner roles. The '
                                      'principle of least privilege should be followed '
                                      'and only necessary privileges should be assigned '
                                      'instead of allowing full administrative access. '
                                      'Classic subscription admin roles offer basic '
                                      'access management and include Account '
                                      'Administrator, Service Administrator, and '
                                      'Co-Administrators. It is recommended the least '
                                      'necessary permissions be given initially. '
                                      'Permissions can be added as needed by the account '
                                      'holder. This ensures the account holder cannot '
                                      'perform actions which were not intended.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'az role definition list\n'
                                      "Check for entries with 'assignableScope' of '/' or "
                                      "a 'subscription', and an action of '*'\n"
                                      'Verify the usage and impact of removing the role '
                                      'identified\n'
                                      'az role definition delete --name "rolename"',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that no custom subscription owner roles are '
                                    'created',
                       'section': '1.23',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '8 Malware Defenses\nMalware Defenses',
                       'description': 'The standard pricing tier enables threat detection '
                                      'for networks and virtual machines, providing '
                                      'threat intelligence, anomaly detection, and '
                                      'behavior analytics in the Azure Security Center. '
                                      'Enabling the Standard pricing tier allows for '
                                      'greater defense-in-depth, with threat detection '
                                      'provided by the Microsoft Security Response Center '
                                      '(MSRC).',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      "1. Go to 'Azure Security Center'\n"
                                      "2. Select 'Security policy' blade\n"
                                      "3. Click On 'Edit Settings' to alter the the "
                                      'security policy for a subscription\n'
                                      "4. Select the 'Pricing tier' blade\n"
                                      "5. Select 'Standard'\n"
                                      "6. Select 'Save'\n"
                                      '\n'
                                      'Azure Command Line Interface 2.0\n'
                                      'Use the below command to set Pricing Tier to '
                                      'Standard.\n'
                                      "'''\n"
                                      'az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/providers/Microsoft. '
                                      'Security/pricings/default?api-version=2017-08-01-preview '
                                      '-d@"input.json"\'\n'
                                      "'''\n"
                                      '\n'
                                      'Where input.json contains the Request body json '
                                      'data as mentioned below.\n'
                                      "'''\n"
                                      '{\n'
                                      ' "id": '
                                      '"/subscriptions//providers/Microsoft.Security/pricings/default",\n'
                                      ' "name": "default",\n'
                                      ' "type": "Microsoft.Security/pricings",\n'
                                      ' "properties": {\n'
                                      ' "pricingTier": "Standard"\n'
                                      ' }\n'
                                      '}\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that standard pricing tier is selected',
                       'section': '2.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '3.1 Run Automated Vulnerability Scanning Tools\n'
                              'Utilize an up-to-date SCAP-compliant vulnerability '
                              'scanning tool to automatically scan all systems on the '
                              'network on a weekly or more frequent basis to identify all '
                              "potential vulnerabilities on the organization's systems.",
                       'description': 'Enable automatic provisioning of the monitoring '
                                      "agent to collect security data. When 'Automatic "
                                      "provisioning of monitoring agent' is turned on, "
                                      'Azure Security Center provisions the Microsoft '
                                      'Monitoring Agent on all existing supported Azure '
                                      'virtual machines and any new ones that are '
                                      'created. The Microsoft Monitoring Agent scans for '
                                      'various security-related configurations and events '
                                      'such as system updates, OS vulnerabilities, '
                                      'endpoint protection, and provides alerts.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      "1. Go to 'Security Center'\n"
                                      "2. Click on 'Security Policy'\n"
                                      '3. Click On "Edit Settings" for each subscription\n'
                                      "4. Click on 'Data Collection'\n"
                                      "5. Set 'Automatic provisioning of monitoring "
                                      "agent' to 'On'\n"
                                      "6. Click 'Save'\n"
                                      '\n'
                                      'Azure Command Line Interface 2.0\n'
                                      "Use the below command to set 'Automatic "
                                      "provisioning of monitoring agent' to 'On'.\n"
                                      "'''\n"
                                      'az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/providers/Microsoft.Security/'
                                      'autoProvisioningSettings/default?api-version=2017-08-01-preview '
                                      '-d@"input.json"\'\n'
                                      "'''\n"
                                      "Where 'input.json' contains the Request body json "
                                      'data as mentioned below.\n'
                                      "'''\n"
                                      ' {\n'
                                      ' "id": '
                                      '"/subscriptions//providers/Microsoft.Security/autoProvisioningSettings/default",\n'
                                      ' "name": "default",\n'
                                      ' "type": '
                                      '"Microsoft.Security/autoProvisioningSettings",\n'
                                      ' "properties": {\n'
                                      ' "autoProvision": "On"\n'
                                      ' }\n'
                                      '}\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Automatic provisioning of monitoring "
                                    "agent' is set to 'On'",
                       'section': '2.2',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '3.4 Deploy Automated Operating System Patch Management '
                              'Tools\n'
                              'Deploy automated software update tools in order to ensure '
                              'that the operating systems are running the most recent '
                              'security updates provided by the software vendor.',
                       'description': 'Enable system updates recommendations for virtual '
                                      'machines. When this setting is enabled, it '
                                      'retrieves a daily list of available security and '
                                      'critical updates from Windows Update or Windows '
                                      'Server Update Services. The retrieved list depends '
                                      "on the service that's configured for that virtual "
                                      'machine and recommends that the missing updates be '
                                      'applied. For Linux systems, the policy uses the '
                                      'distro-provided package management system to '
                                      'determine packages that have available updates. It '
                                      'also checks for security and critical updates from '
                                      'Azure Cloud Services virtual machines.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor system "
                                      "updates' to 'AuditIfNotExists' or any other "
                                      "available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor System '
                                    'Updates" is not "Disabled"',
                       'section': '2.3',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '3.1 Run Automated Vulnerability Scanning Tools\n'
                              '  Utilize an up-to-date SCAP-compliant vulnerability '
                              'scanning tool to automatically scan all systems on the '
                              'network on a weekly or more frequent basis to identify all '
                              "potential vulnerabilities on the organization's systems.",
                       'description': 'Enable Monitor OS vulnerability recommendations '
                                      'for virtual machines. When this setting is '
                                      'enabled, it analyzes operating system '
                                      'configurations daily to determine issues that '
                                      'could make the virtual machine vulnerable to '
                                      'attack. The policy also recommends configuration '
                                      'changes to address these vulnerabilities.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor os "
                                      "Vulnerabilities' to 'AuditIfNotExists' or any "
                                      "other available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor OS '
                                    'Vulnerabilities" is not "Disabled"',
                       'section': '2.4',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '8 Malware Defenses\nMalware Defenses',
                       'description': 'Enable Endpoint protection recommendations for '
                                      'virtual machines. When this setting is enabled, it '
                                      'recommends endpoint protection be provisioned for '
                                      'all Windows virtual machines to help identify and '
                                      'remove viruses, spyware, and other malicious '
                                      'software.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor Endpoint "
                                      "Protection' to 'AuditIfNotExists' or any other "
                                      "available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor Endpoint '
                                    'Protection" is not "Disabled"',
                       'section': '2.5',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '14.8 Encrypt Sensitive Information at Rest\n'
                              'Encrypt all sensitive information at rest using a tool '
                              'that requires a secondary authentication mechanism not '
                              'integrated into the operating system, in order to access '
                              'the information.',
                       'description': 'Enable Disk encryption recommendations for virtual '
                                      'machines. When this setting is enabled, it '
                                      'recommends enabling disk encryption in all virtual '
                                      'machines (Windows and Linux as well) to enhance '
                                      'data protection at rest.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor Disk "
                                      "Encryption' to 'AuditIfNotExists' or any other "
                                      "available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor Disk '
                                    'Encryption" is not "Disabled"',
                       'section': '2.6',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '12 Boundary Defense\nBoundary Defense',
                       'description': 'Enable Network security group recommendations for '
                                      'virtual machines. When this setting is enabled, it '
                                      'recommends that network security groups be '
                                      'configured to control inbound and outbound traffic '
                                      'to VMs that have public endpoints. Network '
                                      'security groups that are configured for a subnet '
                                      'are inherited by all virtual machine network '
                                      'interfaces unless otherwise specified. In addition '
                                      'to checking that a network security group has been '
                                      'configured, this policy assesses inbound security '
                                      'rules to identify rules that allow incoming '
                                      'traffic.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor Network "
                                      "Security Groups' to 'AuditIfNotExists' or any "
                                      "other available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor Network '
                                    'Security Groups" is not "Disabled"',
                       'section': '2.7',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '12 Boundary Defense\nBoundary Defense',
                       'description': 'Enable Web application firewall recommendations '
                                      'for virtual machines. When this setting is '
                                      'enabled, it recommends that a web application '
                                      'firewall is provisioned on virtual machines when '
                                      'either of the following is true: \n'
                                      '- Instance-level public IP (ILPIP) is used and the '
                                      'inbound security rules for the associated network '
                                      'security group are configured to allow access to '
                                      'port 80/443.\n'
                                      '- Load-balanced IP is used and the associated load '
                                      'balancing and inbound network address translation '
                                      '(NAT) rules are configured to allow access to port '
                                      '80/443.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor Web "
                                      "Application Firewall' to 'AuditIfNotExists' or any "
                                      "other available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor Web '
                                    'Application Firewall" is not "Disabled"',
                       'section': '2.8',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '11 Secure Configuration for Network Devices, such as '
                              'Firewalls, Routers and Switches\n'
                              'Secure Configuration for Network Devices, such as '
                              'Firewalls, Routers and Switches',
                       'description': 'Enable next generation firewall recommendations '
                                      'for virtual machines. When this setting is '
                                      'enabled, it extends network protections beyond '
                                      'network security groups, which are built into '
                                      'Azure. Security Center will search for deployments '
                                      'where a next generation firewall is recommended '
                                      'and enable a virtual appliance to be provisioned.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Enable Next "
                                      "Generation Firewall(NGFW) Monitoring' to "
                                      "'AuditIfNotExists' or any other available value "
                                      "than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Enable Next '
                                    'Generation Firewall(NGFW) Monitoring" is not '
                                    '"Disabled"',
                       'section': '2.9',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '3.1 Run Automated Vulnerability Scanning Tools\n'
                              'Utilize an up-to-date SCAP-compliant vulnerability '
                              'scanning tool to automatically scan all systems on the '
                              'network on a weekly or more frequent basis to identify all '
                              "potential vulnerabilities on the organization's systems. ",
                       'description': 'Enable vulnerability assessment recommendations '
                                      'for virtual machines. When this setting is '
                                      'enabled, it recommends a vulnerability assessment '
                                      'solution be installed on the VM.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor "
                                      "Vulnerability Assessment' to 'AuditIfNotExists' or "
                                      "any other available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor '
                                    'Vulnerability Assessment" is not "Disabled"',
                       'section': '2.10',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '13 Data Protection\nData Protection',
                       'description': 'Enable storage encryption recommendations. When '
                                      'this setting is enabled, any new data in Azure '
                                      'Blobs and Files will be encrypted.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor Storage "
                                      "Blob Encryption' to 'Audit' or any other available "
                                      "value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor Storage '
                                    'Blob Encryption" is not "Disabled"',
                       'section': '2.11',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '9.4 Apply Host-based Firewalls or Port Filtering\n'
                              'Apply host-based firewalls or port filtering tools on end '
                              'systems, with a default-deny rule that drops all traffic '
                              'except those services and ports that are explicitly '
                              'allowed. ',
                       'description': 'Enable JIT Network Access for virtual machines. '
                                      'When this setting is enabled, Security Center '
                                      'locks down inbound traffic to the Azure VMs by '
                                      'creating an NSG rule. The user can select the '
                                      'ports on the VM where inbound traffic should be '
                                      'locked down. Just in time virtual machine (VM) '
                                      'access can be used to lock.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      "1. Navigate to 'Azure Policy'\n"
                                      '2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      '3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      "4. In section 'PARAMETERS', Set 'Monitor JIT "
                                      "Network Access' to 'AuditIfNotExists' or any other "
                                      "available value than 'Disabled'\n"
                                      "5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor JIT '
                                    'Network Access" is not "Disabled"',
                       'section': '2.12',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '2.7 Utilize Application Whitelisting\n'
                              'Utilize application whitelisting technology on all assets '
                              'to ensure that only authorized software executes and all '
                              'unauthorized software is blocked from executing on '
                              'assets. ',
                       'description': 'Enable adaptive application controls. Adaptive '
                                      'application controls help control which '
                                      'applications can run on VMs located in Azure, '
                                      'which among other benefits helps harden those VMs '
                                      'against malware. The Security Center uses machine '
                                      'learning to analyze the processes running in the '
                                      'VM and helps to apply white-listing rules using '
                                      'this intelligence.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor "
                                      "Application Whitelisting' to 'AuditIfNotExists' or "
                                      "any other available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor Adaptive '
                                    'Application Whitelisting" is not "Disabled"',
                       'section': '2.13',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '6.2 Activate audit logging\n'
                              'Ensure that local logging has been enabled on all systems '
                              'and networking devices.',
                       'description': 'Enable SQL auditing recommendations. When this '
                                      'setting is enabled, it recommends that access '
                                      'auditing for the Azure Database be enabled for '
                                      'compliance, advanced threat detection, and for '
                                      'investigation purposes.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor SQL "
                                      "Auditing' to 'AuditIfNotExists' or any other "
                                      "available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor SQL '
                                    'Auditing" is not "Disabled"',
                       'section': '2.14',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '14.8 Encrypt Sensitive Information at Rest\n'
                              'Encrypt all sensitive information at rest using a tool '
                              'that requires a secondary authentication mechanism not '
                              'integrated into the operating system, in order to access '
                              'the information.',
                       'description': 'Enable SQL encryption recommendations. When this '
                                      'setting is enabled, it recommends that encryption '
                                      'at rest be enabled for the Azure SQL Database, '
                                      'associated backups, and transaction log files. In '
                                      'the event of a data breach, it will not be '
                                      'readable.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Navigate to 'Azure Policy'\n"
                                      ' 2. On Policy "Overview" blade, Click on Policy '
                                      "'ASC Default (Subscription:Subscription_ID)'\n"
                                      ' 3. On "ASC Default" blade, Click on \'Edit '
                                      "Assignments'\n"
                                      " 4. In section 'PARAMETERS', Set 'Monitor SQL "
                                      "Encryption' to 'AuditIfNotExists' or any other "
                                      "available value than 'Disabled'\n"
                                      " 5. Click 'Save'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure ASC Default policy setting "Monitor SQL '
                                    'Encryption" is not "Disabled"',
                       'section': '2.15',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '3 Continuous Vulnerability Management\n'
                              'Continuous Vulnerability Management',
                       'description': 'Provide a security contact email address. '
                                      'Microsoft reaches out to the designated security '
                                      'contact in case its security team finds that the '
                                      "organization's resources are compromised. This "
                                      'ensures that the proper people are aware of any '
                                      'potential compromise in order to mitigate the risk '
                                      'in a timely fashion.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'Security Center'\n"
                                      " 2. Click on 'Security Policy'\n"
                                      " 3. Click On 'Edit Settings' for the security "
                                      'policy subscription\n'
                                      " 4. Click on 'Email notifications'\n"
                                      ' 5. Set a valid email address for the security '
                                      'contact\n'
                                      " 6. Click 'Save'\n"
                                      ' \n'
                                      ' Azure Command Line Interface 2.0\n'
                                      " Use the below command to set 'Security contact "
                                      "emails' to 'On'.\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/providers/Microsoft.Security/'
                                      'securityContacts/default1?api-version=2017-08-01-preview '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      " Where 'input.json' contains the Request body json "
                                      'data as mentioned below. And replace '
                                      'validEmailAddress with email ids csv for '
                                      'multiple.\n'
                                      " '''\n"
                                      '  {\n'
                                      '  "id": '
                                      '"/subscriptions//providers/Microsoft.Security/securityContacts/default1",\n'
                                      '  "name": "default1",\n'
                                      '  "type": "Microsoft.Security/securityContacts",\n'
                                      '  "properties": {\n'
                                      '  "email": "",\n'
                                      '  "phone": "\n'
                                      ' ",\n'
                                      '  "alertNotifications": "On",\n'
                                      '  "alertsToAdmins": "On"\n'
                                      ' }\n'
                                      '  }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Security contact emails' is set",
                       'section': '2.16',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '3 Continuous Vulnerability Management\n'
                              'Continuous Vulnerability Management',
                       'description': 'Provide a security contact phone number. Microsoft '
                                      'reaches out to the designated security contact in '
                                      'case its security team finds that the '
                                      "organization's resources are compromised. This "
                                      'ensures that the proper people are aware of any '
                                      'potential compromise in order to mitigate the risk '
                                      'in a timely fashion. Before taking any action, '
                                      'make sure that the information provided is valid, '
                                      'as the communication is not digitally signed.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'Security Center'\n"
                                      " 2. Click on 'Security Policy'\n"
                                      " 3. Click On 'Edit Settings' for the security "
                                      'policy subscription\n'
                                      " 4. Click on 'Email notifications'\n"
                                      ' 5. Set a valid security contact Phone number\n'
                                      " 6. Click 'Save'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      " Use the below command to set 'security contact "
                                      "'Phone number''.\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/providers/Microsoft.Security/securityContacts/default1?api-version=2017-08-01-preview '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      " Where 'input.json' contains the Request body json "
                                      'data as mentioned below.\n'
                                      " And replace 'validEmailAddress' with email ids "
                                      "csv for multiple and 'phoneNumber' with valid "
                                      'phone number.\n'
                                      " '''\n"
                                      '  {\n'
                                      '  "id": '
                                      '"/subscriptions//providers/Microsoft.Security/securityContacts/default1",\n'
                                      '  "name": "default1",\n'
                                      '  "type": "Microsoft.Security/securityContacts",\n'
                                      '  "properties": {\n'
                                      '  "email": "",\n'
                                      '  "phone": "\n'
                                      ' ",\n'
                                      '  "alertNotifications": "On",\n'
                                      '  "alertsToAdmins": "On"\n'
                                      '  }\n'
                                      '  }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that security contact 'Phone number' is set",
                       'section': '2.17',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '3 Continuous Vulnerability Management\n'
                              'Continuous Vulnerability Management',
                       'description': 'Enable emailing security alerts to the security '
                                      'contact. Enabling security alert emails ensures '
                                      'that security alert emails are received from '
                                      'Microsoft. This ensures that the right people are '
                                      'aware of any potential security issues and are '
                                      'able to mitigate the risk.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'Security Center'\n"
                                      " 2. Click on 'Security Policy'\n"
                                      " 3. Click On 'Edit Settings' for the security "
                                      'policy subscription\n'
                                      " 4. Click on 'Email notifications'\n"
                                      " 5. Set 'Send email notification for high severity "
                                      "alerts' to 'On'\n"
                                      " 6. Click 'Save'\n"
                                      ' \n'
                                      ' Azure Command Line Interface 2.0\n'
                                      " Use the below command to set 'Send email "
                                      "notification for high severity alerts' to 'On'.\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/providers/Microsoft.Security/'
                                      'securityContacts/default1?api-version=2017-08-01-preview '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      " Where 'input.json' contains the Request body json "
                                      'data as mentioned below.\n'
                                      " And replace 'validEmailAddress' with email ids "
                                      "csv for multiple and 'phoneNumber' with valid "
                                      'phone number.\n'
                                      " '''\n"
                                      '  {\n'
                                      '  "id": '
                                      '"/subscriptions//providers/Microsoft.Security/securityContacts/default1",\n'
                                      '  "name": "default1",\n'
                                      '  "type": "Microsoft.Security/securityContacts",\n'
                                      '  "properties": {\n'
                                      '  "email": "",\n'
                                      '  "phone": "\n'
                                      ' ",\n'
                                      '  "alertNotifications": "On",\n'
                                      '  "alertsToAdmins": "On"\n'
                                      '  }\n'
                                      '  }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Send email notification for high "
                                    "severity alerts' is set to 'On'",
                       'section': '2.18',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Security Center',
                       'cis': '3 Continuous Vulnerability Management\n'
                              'Continuous Vulnerability Management',
                       'description': 'Enable security alert emails to subscription '
                                      'owners. Enabling security alert emails to '
                                      'subscription owners ensures that they receive '
                                      'security alert emails from Microsoft. This ensures '
                                      'that they are aware of any potential security '
                                      'issues and can mitigate the risk in a timely '
                                      'fashion.',
                       'entities_results': '',
                       'remediation': 'Azure Console \n'
                                      " 1. Go to 'Security Center'\n"
                                      " 2. Click on 'Security Policy'\n"
                                      " 3. Click On 'Edit Settings' for the security "
                                      'policy subscription\n'
                                      " 4. Click on 'Email notifications'\n"
                                      " 5. Set 'Send email also to subscription owners' "
                                      "to 'On'\n"
                                      " 6. Click 'Save'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      " Use the below command to set 'Send email also to "
                                      "subscription owners' to 'On'.\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/providers/Microsoft.Security/'
                                      'securityContacts/default1?api-version=2017-08-01-preview '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      " Where 'input.json' contains the Request body json "
                                      'data as mentioned below.\n'
                                      " And replace 'validEmailAddress' with email ids "
                                      "csv for multiple and 'phoneNumber' with valid "
                                      'phone number.\n'
                                      " '''\n"
                                      '  {\n'
                                      '  "id": '
                                      '"/subscriptions//providers/Microsoft.Security/securityContacts/default1",\n'
                                      '  "name": "default1",\n'
                                      '  "type": "Microsoft.Security/securityContacts",\n'
                                      '  "properties": {\n'
                                      '  "email": "",\n'
                                      '  "phone": "\n'
                                      ' ",\n'
                                      '  "alertNotifications": "On",\n'
                                      '  "alertsToAdmins": "On"\n'
                                      '  }\n'
                                      '  }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Send email also to subscription owners' "
                                    "is set to 'On'",
                       'section': '2.19',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Storage Accounts',
                       'cis': '14.4 Encrypt All Sensitive Information in Transit\n'
                              'Encrypt all sensitive information in transit',
                       'description': 'Enable data encryption is transit. The secure '
                                      'transfer option enhances the security of a storage '
                                      'account by only allowing requests to the storage '
                                      'account by a secure connection. For example, when '
                                      'calling REST APIs to access storage accounts, the '
                                      'connection must use HTTPS. Any requests using HTTP '
                                      "will be rejected when 'secure transfer required' "
                                      'is enabled. When using the Azure files service, '
                                      'connection without encryption will fail, including '
                                      'scenarios using SMB 2.1, SMB 3.0 without '
                                      'encryption, and some flavors of the Linux SMB '
                                      'client. Because Azure storage doesn’t support '
                                      'HTTPS for custom domain names, this option is not '
                                      'applied when using a custom domain name.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      "1. Go to 'Storage Accounts'\n"
                                      '2. For each storage account, go to '
                                      "'Configuration'\n"
                                      "3. Set 'Secure transfer required' to 'Enabled'\n"
                                      '\n'
                                      'Azure Command Line Interface 2.0\n'
                                      "Use the below command to enable 'Secure transfer "
                                      "required' for a 'Storage Account'\n"
                                      " '''\n"
                                      'az storage account update --name  '
                                      '--resource-group  --https-only true\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Secure transfer required' is set to "
                                    "'Enabled'",
                       'section': '3.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Storage Accounts',
                       'cis': '16 Account Monitoring and Control\n'
                              'Account Monitoring and Control',
                       'description': 'Disable anonymous access to blob containers. '
                                      'Anonymous, public read access to a container and '
                                      'its blobs can be enabled in Azure Blob storage. It '
                                      'grants read-only access to these resources without '
                                      'sharing the account key, and without requiring a '
                                      'shared access signature. It is recommended not to '
                                      'provide anonymous access to blob containers until, '
                                      'and unless, it is strongly desired. A shared '
                                      'access signature token should be used for '
                                      'providing controlled and timed access to blob '
                                      'containers.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      'First, follow Microsoft documentation and created '
                                      'shared access signature tokens for your blob '
                                      'containers. Then, \n'
                                      "1. Go to 'Storage Accounts'\n"
                                      "2. For each storage account, go to 'Containers' "
                                      "under 'BLOB SERVICE'\n"
                                      "3. For each container, click 'Access policy'\n"
                                      "4. Set 'Public access level' to 'Private (no "
                                      "anonymous access)'\n"
                                      '\n'
                                      'Azure Command Line Interface 2.0\n'
                                      '1. Identify the container name from the audit '
                                      'command\n'
                                      '2. Set the permission for public access to '
                                      "'private'(off) for the above container name, using "
                                      'the below command\n'
                                      " '''\n"
                                      'az storage container set-permission --name  '
                                      '--public-access off --account-name  '
                                      '--account-key \n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Public access level' is set to Private "
                                    'for blob containers',
                       'section': '3.6',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Storage Accounts',
                       'cis': '16 Account Monitoring and Control\n'
                              'Account Monitoring and Control',
                       'description': 'Restricting default network access helps to '
                                      'provide a new layer of security, since storage '
                                      'accounts accept connections from clients on any '
                                      'network. To limit access to selected networks, the '
                                      'default action must be changed. Storage accounts '
                                      'should be configured to deny access to traffic '
                                      'from all networks (including internet traffic). '
                                      'Access can be granted to traffic from specific '
                                      'Azure Virtual networks, allowing a secure network '
                                      'boundary for specific applications to be built. '
                                      'Access can also be granted to public internet IP '
                                      'address ranges, to enable connections from '
                                      'specific internet or on-premises clients. When '
                                      'network rules are configured, only applications '
                                      'from allowed networks can access a storage '
                                      'account. When calling from an allowed network, '
                                      'applications continue to require proper '
                                      'authorization (a valid access key or SAS token) to '
                                      'access the storage account.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      "1. Go to 'Storage Accounts'\n"
                                      '2. For each storage account, Click on the '
                                      "'settings' menu called 'Firewalls' and 'virtual "
                                      "networks'.\n"
                                      '3. Ensure that you have elected to allow access '
                                      "from 'Selected networks'.\n"
                                      "4. Add rules to 'allow traffic' from 'specific "
                                      "network'.\n"
                                      '4. Click Save to apply your changes.\n'
                                      '\n'
                                      'Azure Command Line Interface 2.0\n'
                                      "Use the below command to update 'default-action' "
                                      "to 'Deny'.\n"
                                      " '''\n"
                                      ' az storage account update --name  '
                                      '--resource-group  --default-action Deny\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure default network access rule for Storage '
                                    'Accounts is set to deny',
                       'section': '3.7',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Enable auditing on SQL Servers. The Azure platform '
                                      'allows a SQL server to be created as a service. '
                                      'Enabling auditing at the server level ensures that '
                                      'all existing and newly created databases on the '
                                      'SQL server instance are audited. Auditing policy '
                                      'applied on the SQL database does not override '
                                      'auditing policy and settings applied on the '
                                      'particular SQL server where the database is '
                                      'hosted.\n'
                                      'Auditing tracks database events and writes them to '
                                      'an audit log in the Azure storage account. It also '
                                      'helps to maintain regulatory compliance, '
                                      'understand database activity, and gain insight '
                                      'into discrepancies and anomalies that could '
                                      'indicate business concerns or suspected security '
                                      'violations.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      ' 2. For each server instance\n'
                                      " 3. Click on 'Auditing'\n"
                                      " 4. Set 'Auditing' to 'On'\n"
                                      ' \n'
                                      'Azure PowerShell \n'
                                      'Get the list of all SQL Servers \n'
                                      " '''\n"
                                      ' Get-AzureRmSqlServer\n'
                                      " '''\n"
                                      ' \n'
                                      ' For each Server, enable auditing. \n'
                                      " '''\n"
                                      ' Set-AzureRmSqlServerAuditingPolicy '
                                      '-ResourceGroupName -ServerName -AuditType '
                                      '-StorageAccountName \n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Auditing' is set to 'On'",
                       'section': '4.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': "Configure the 'AuditActionGroups' property to "
                                      'appropriate groups to capture all the critical '
                                      'activities on the SQL Server and all the SQL '
                                      'databases hosted on the SQL server. To capture all '
                                      'critical activities done on SQL Servers and '
                                      'databases within sql servers, auditing should be '
                                      'configured to capture appropriate '
                                      "'AuditActionGroups'. Property 'AuditActionGroup' "
                                      'should contains at least '
                                      "'SUCCESSFUL_DATABASE_AUTHENTICATION_GROUP, "
                                      'FAILED_DATABASE_AUTHENTICATION_GROUP, '
                                      "BATCH_COMPLETED_GROUP' to ensure comprehensive "
                                      'audit logging for SQL servers and SQL databases '
                                      'hosted on SQL Server.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      ' On Azure Console, There is no Provision to check '
                                      "or change 'AuditActionGroup' property. \n"
                                      ' \n'
                                      'Azure PowerShell \n'
                                      ' To create Audit profile with prescribed '
                                      "'AuditActionGroup': \n"
                                      " '''\n"
                                      ' Set-AzureRmSqlServerAuditingPolicy '
                                      '-ResourceGroupName "" -ServerName "" '
                                      '-StorageAccountName "storageAccountName" '
                                      '-AuditActionGroup '
                                      '"SUCCESSFUL_DATABASE_AUTHENTICATION_GROUP", '
                                      '"FAILED_DATABASE_AUTHENTICATION_GROUP" '
                                      '-RetentionInDays = 90>\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'AuditActionGroups' in 'auditing' policy "
                                    'for a SQL server is set properly',
                       'section': '4.2',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.4 Ensure adequate storage for logs\n'
                              'Ensure that all systems that store logs have adequate '
                              'storage space for the logs generated',
                       'description': 'SQL Server Audit Retention should be configured to '
                                      'be greater than 90 days. Audit Logs can be used to '
                                      'check for anomalies and give insight into '
                                      'suspected breaches or misuse of information and '
                                      'access.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      ' 2. For each server instance\n'
                                      " 3. Click on 'Auditing'\n"
                                      " 4. Select 'Storage Details'\n"
                                      " 5. Set 'Retention (days)' setting 'greater than "
                                      "90 days'\n"
                                      " 6. Select 'OK'\n"
                                      " 7. Select 'Save'\n"
                                      ' \n'
                                      'Azure PowerShell \n'
                                      ' For each Server, set retention policy for more '
                                      'than or equal to 90 days \n'
                                      " '''\n"
                                      ' set-AzureRmSqlServerAuditing -ResourceGroupName '
                                      '-ServerName -RetentionInDays \n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Auditing' Retention is 'greater than 90 "
                                    "days'",
                       'section': '4.3',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '3.1 Run Automated Vulnerability Scanning Tools\n'
                              'Utilize an up-to-date SCAP-compliant vulnerability '
                              'scanning tool to automatically scan all systems on the '
                              'network on a weekly or more frequent basis to identify all '
                              "potential vulnerabilities on the organization's systems.",
                       'description': 'Enable "Advanced Data Security" on critical SQL '
                                      'Servers. SQL Server "Advanced Data Security" '
                                      'provides a new layer of security, which enables '
                                      'customers to detect and respond to potential '
                                      'threats as they occur by providing security alerts '
                                      'on anomalous activities. Users will receive an '
                                      'alert upon suspicious database activities, '
                                      'potential vulnerabilities, and SQL injection '
                                      'attacks, as well as anomalous database access '
                                      'patterns. SQL Server Threat Detection alerts '
                                      'provide details of suspicious activity and '
                                      'recommend action on how to investigate and '
                                      'mitigate the threat. Additionally, SQL server '
                                      'Advanced Data Security includes functionality for '
                                      'discovering and classifying sensitive data. '
                                      'Advanced Data Security is a paid feature. It is '
                                      'recommended to enable the feature at least on '
                                      'business-critical SQL Servers.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      ' 2. For each server instance\n'
                                      " 3. Click on 'Advanced Data Security'\n"
                                      " 4. Set 'Advanced Data Security' to 'On'\n"
                                      ' \n'
                                      'Azure PowerShell \n'
                                      " Enable 'Advanced Data Security' for a SQL "
                                      'Server:  \n'
                                      " '''\n"
                                      ' Set-AzureRmSqlServerThreatDetectionPolicy '
                                      '-ResourceGroupName -ServerName -EmailAdmins $True\n'
                                      " ''' \n"
                                      ' Note:\n'
                                      " - Enabling 'Advanced Data Security' from the "
                                      "Azure portal enables 'Threat Detection'\n"
                                      ' - Using Powershell command '
                                      "'Set-AzureRmSqlServerThreatDetectionPolicy' "
                                      "enables 'Advanced Data Security' for a SQL server",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Advanced Data Security' on a SQL server "
                                    "is set to 'On'",
                       'section': '4.4',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '3.1 Run Automated Vulnerability Scanning Tools\n'
                              'Utilize an up-to-date SCAP-compliant vulnerability '
                              'scanning tool to automatically scan all systems on the '
                              'network on a weekly or more frequent basis to identify all '
                              "potential vulnerabilities on the organization's systems.",
                       'description': 'Enable all types of threat detection on SQL '
                                      'servers. Enabling all threat detection types '
                                      'protects against SQL injection, database '
                                      'vulnerabilities, and any other anomalous '
                                      'activities.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      ' 2. For each server instance\n'
                                      " 3. Click on 'Advanced Data Security'\n"
                                      ' 4. At section Threat Detection Settings, Set '
                                      "'Threat Detection types' to 'All'\n"
                                      ' \n'
                                      'Azure PowerShell \n'
                                      " For each Server, set 'ExcludedDetectionTypes' to "
                                      'None: \n'
                                      " '''\n"
                                      ' Set-AzureRmSqlServerThreatDetectionPolicy '
                                      '-ResourceGroupName -ServerName '
                                      '-ExcludedDetectionType "None"\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Threat Detection types' is set to 'All'",
                       'section': '4.5',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '19 Incident Response and Management\n'
                              'Incident Response and Management',
                       'description': 'Provide the email address where alerts will be '
                                      'sent when anomalous activities are detected on SQL '
                                      'servers. Providing the email address to receive '
                                      'alerts ensures that any detection of anomalous '
                                      'activities is reported as soon as possible, making '
                                      'it more likely to mitigate any potential risk '
                                      'sooner.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      ' 2. For each server instance\n'
                                      " 3. Click on 'Advanced Threat Protection'\n"
                                      " 4. Set 'Send alerts to' as appropriate\n"
                                      ' \n'
                                      '*Azure PowerShell\n'
                                      " For each Server, set 'Send alerts to' \n"
                                      " '''\n"
                                      ' Set-AzureRmSqlServerThreatDetectionPolicy '
                                      '-ResourceGroupName -ServerName '
                                      '-NotificationRecipientsEmails ""\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Send alerts to' is set",
                       'section': '4.6',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '19 Incident Response and Management\n'
                              'Incident Response and Management',
                       'description': 'Enable service and co-administrators to receive '
                                      'security alerts from the SQL server. Providing the '
                                      'email address to receive alerts ensures that any '
                                      'detection of anomalous activities is reported as '
                                      'soon as possible, making it more likely to '
                                      'mitigate any potential risk sooner.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      ' 2. For each server instance\n'
                                      " 3. Click on 'Advanced Data Security'\n"
                                      ' 4. At section Threat Detection Settings, Enable '
                                      "'Email service and co-administrators'\n"
                                      ' \n'
                                      'Azure PowerShell \n'
                                      " For each Server, 'enable' 'Email service and "
                                      "co-administrators' \n"
                                      " '''\n"
                                      ' Set-AzureRmSqlServerThreatDetectionPolicy '
                                      '-ResourceGroupName -ServerName -EmailAdmins $True\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Email service and co-administrators' is "
                                    "'Enabled'",
                       'section': '4.7',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '16.2 Configure Centralized Point of Authentication\n'
                              'Configure access for all accounts through as few '
                              'centralized points of authentication as possible, '
                              'including network, security, and cloud systems',
                       'description': 'Use Azure Active Directory Authentication for '
                                      'authentication with SQL Database. Azure Active '
                                      'Directory authentication is a mechanism to connect '
                                      'to Microsoft Azure SQL Database and SQL Data '
                                      'Warehouse using identities in Azure Active '
                                      'Directory (Azure AD). With Azure AD '
                                      'authentication, identities of database users and '
                                      'other Microsoft services can be managed in one '
                                      'central location. Central ID management provides a '
                                      'single place to manage database users and '
                                      'simplifies permission management.\n'
                                      ' - It provides an alternative to SQL Server '
                                      'authentication.\n'
                                      ' - Helps stop the proliferation of user identities '
                                      'across database servers.\n'
                                      ' - Allows password rotation in a single place.\n'
                                      ' - Customers can manage database permissions using '
                                      'external (AAD) groups.\n'
                                      ' - It can eliminate storing passwords by enabling '
                                      'integrated Windows authentication and other forms '
                                      'of authentication supported by Azure Active '
                                      'Directory.\n'
                                      ' - Azure AD authentication uses contained database '
                                      'users to authenticate identities at the database '
                                      'level.\n'
                                      ' - Azure AD supports token-based authentication '
                                      'for applications connecting to SQL Database.\n'
                                      ' - Azure AD authentication supports ADFS (domain '
                                      'federation) or native user/password authentication '
                                      'for a local Azure Active Directory without domain '
                                      'synchronization.\n'
                                      ' - Azure AD supports connections from SQL Server '
                                      'Management Studio that use Active Directory '
                                      'Universal Authentication, which includes '
                                      'Multi-Factor Authentication (MFA). MFA includes '
                                      'strong authentication with a range of easy '
                                      'verification options — phone call, text message, '
                                      'smart cards with pin, or mobile app notification.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      " 2. For each SQL server, click on 'Active "
                                      "Directory admin'\n"
                                      " 3. Click on 'Set admin'\n"
                                      ' 4. Select an admin\n'
                                      " 5. Click 'Save'\n"
                                      ' \n'
                                      'Azure PowerShell \n'
                                      ' For each Server, set AD Admin \n'
                                      " '''\n"
                                      ' Set-AzureRmSqlServerActiveDirectoryAdministrator '
                                      '-ResourceGroupName -ServerName -DisplayName ""\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Azure Active Directory Admin is '
                                    'configured',
                       'section': '4.8',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '14.8 Encrypt Sensitive Information at Rest\n'
                              'Encrypt all sensitive information at rest using a tool '
                              'that requires a secondary authentication mechanism not '
                              'integrated into the operating system, in order to access '
                              'the information',
                       'description': 'Enable Transparent Data Encryption on every SQL '
                                      'server. Azure SQL Database transparent data '
                                      'encryption helps protect against the threat of '
                                      'malicious activity by performing real-time '
                                      'encryption and decryption of the database, '
                                      'associated backups, and transaction log files at '
                                      'rest without requiring changes to the application.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL databases'\n"
                                      ' 2. For each DB instance\n'
                                      " 3. Click on 'Transparent data encryption'\n"
                                      " 4. Set 'Data encryption' to 'On'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      " Use the below command to enable 'Transparent data "
                                      "encryption' for SQL DB instance. \n"
                                      " '''\n"
                                      ' az sql db tde set --resource-group --server '
                                      '--database --status Enabled\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Data encryption' is set to 'On' on a "
                                    'SQL Database',
                       'section': '4.9',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '16.4 Encrypt or Hash all Authentication Credentials\n'
                              'Encrypt or hash with a salt all authentication credentials '
                              'when stored',
                       'description': 'TDE with BYOK support provides increased '
                                      'transparency and control over the TDE Protector, '
                                      'increased security with an HSM-backed external '
                                      'service, and promotion of separation of duties. '
                                      'With TDE, data is encrypted at rest with a '
                                      'symmetric key (called the database encryption key) '
                                      'stored in the database or data warehouse '
                                      'distribution. To protect this data encryption key '
                                      '(DEK) in the past, only a certificate that the '
                                      'Azure SQL Service managed could be used. Now, with '
                                      'BYOK support for TDE, the DEK can be protected '
                                      'with an asymmetric key that is stored in the Key '
                                      'Vault. Key Vault is a highly available and '
                                      'scalable cloud-based key store which offers '
                                      'central key management, leverages FIPS 140-2 Level '
                                      '2 validated hardware security modules (HSMs), and '
                                      'allows separation of management of keys and data, '
                                      'for additional security. Based on business needs '
                                      'or criticality of data/databases hosted a SQL '
                                      'server, it is recommended that the TDE protector '
                                      'is encrypted by a key that is managed by the data '
                                      'owner (BYOK). Bring Your Own Key (BYOK) support '
                                      'for Transparent Data Encryption (TDE) allows user '
                                      'control of TDE encryption keys and restricts who '
                                      'can access them and when. Azure Key Vault, Azure’s '
                                      'cloud-based external key management system is the '
                                      'first key management service where TDE has '
                                      'integrated support for BYOK. With BYOK, the '
                                      'database encryption key is protected by an '
                                      'asymmetric key stored in the Key Vault. The '
                                      'asymmetric key is set at the server level and '
                                      'inherited by all databases under that server. This '
                                      'feature is currently in preview and we do not '
                                      'recommend using it for production workloads until '
                                      'we declare General Availability.',
                       'entities_results': '',
                       'remediation': 'Azure Console:\n'
                                      " Go to 'SQL servers' \n"
                                      ' For the desired server instance \n'
                                      " 1. Click On 'Transparent data encryption'\n"
                                      " 2. Set 'Use your own key' to 'YES'\n"
                                      " 3. Browse through your 'key vaults' to Select an "
                                      'existing key or create a new key in Key Vault.\n'
                                      " 4. Check 'Make selected key the default TDE "
                                      "protector'\n"
                                      ' \n'
                                      'Azure CLI: \n'
                                      " Use the below command to encrypt SQL server's TDE "
                                      'protector with BYOK\n'
                                      " '''\n"
                                      ' az sql server tde-key >> Set --resource-group '
                                      '--server --server-key-type {AzureKeyVault} [--kid '
                                      ']\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure SQL server's TDE protector is encrypted with "
                                    'BYOK (Use your own key)\n',
                       'section': '4.10',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '14.4 Encrypt All Sensitive Information in Transit\n'
                              'Encrypt all sensitive information in transit',
                       'description': "Enable 'SSL connection' on 'MYSQL' Servers. SSL "
                                      'connectivity helps to provide a new layer of '
                                      'security, by connecting database server to client '
                                      'applications using Secure Sockets Layer (SSL). '
                                      'Enforcing SSL connections between database server '
                                      'and client applications helps protect against "man '
                                      'in the middle" attacks by encrypting the data '
                                      'stream between the server and application.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com\n'
                                      " 2. Go to 'Azure Database' for 'MySQL server'\n"
                                      " 3. For each database, click on 'Connection "
                                      "security'\n"
                                      " 4. In 'SSL' settings\n"
                                      " 5. Click on 'ENABLED' for 'Enforce SSL "
                                      "connection'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      ' Use the below command to set MYSQL Databases to '
                                      'Enforce SSL connection. \n'
                                      'az mysql server update --resource-group --name '
                                      '--ssl-enforcement Enabled',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure 'Enforce SSL connection' is set to 'ENABLED' "
                                    'for MySQL Database Server',
                       'section': '4.11',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.2 Activate audit logging\n'
                              'Ensure that local logging has been enabled on all systems '
                              'and networking devices',
                       'description': "Enable 'log_checkpoints' on 'PostgreSQL Servers'. "
                                      "Enabling 'log_checkpoints' helps the PostgreSQL "
                                      "Database to 'Log each checkpoint' in turn "
                                      'generates query and error logs. However, access to '
                                      'transaction logs is not supported. Query and error '
                                      'logs can be used to identify, troubleshoot, and '
                                      'repair configuration errors and sub-optimal '
                                      'performance.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com\n'
                                      ' 2. Go to Azure Database for PostgreSQL server\n'
                                      ' 3. For each database, click on Server parameters\n'
                                      " 4. Search for 'log_checkpoints'.\n"
                                      " 5. Click 'ON' and save.\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      " Use the below command to update 'log_checkpoints' "
                                      'configuration. \n'
                                      'az postgres server configuration set '
                                      '--resource-group --server-name --name '
                                      'log_checkpoints --value on',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure server parameter 'log_checkpoints' is set to "
                                    "'ON' for PostgreSQL Database Server",
                       'section': '4.12',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '14.4 Encrypt All Sensitive Information in Transit\n'
                              'Encrypt all sensitive information in transit',
                       'description': "Enable 'SSL connection' on 'PostgreSQL' Servers. "
                                      "'SSL connectivity' helps to provide a new layer of "
                                      'security, by connecting database server to client '
                                      'applications using Secure Sockets Layer (SSL). '
                                      'Enforcing SSL connections between database server '
                                      'and client applications helps protect against "man '
                                      'in the middle" attacks by encrypting the data '
                                      'stream between the server and application.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com\n'
                                      " 2. Go to Azure Database for 'PostgreSQL server'\n"
                                      " 3. For each database, click on 'Connection "
                                      "security'\n"
                                      " 4. In 'SSL' settings.\n"
                                      " 5. Click on 'ENABLED' to Enforce SSL connection\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      " Use the below command to 'enforce ssl connection' "
                                      "for 'PostgreSQL' Database. \n"
                                      'az postgres server update --resource-group --name '
                                      '--ssl-enforcement Enabled',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure 'Enforce SSL connection' is set to 'ENABLED' "
                                    'for PostgreSQL Database Server',
                       'section': '4.13',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.2 Activate audit logging\n'
                              'Ensure that local logging has been enabled on all systems '
                              'and networking devices',
                       'description': "Enable 'log_connections' on 'PostgreSQL Servers'. "
                                      "Enabling 'log_connections' helps PostgreSQL "
                                      'Database to log attempted connection to the '
                                      'server, as well as successful completion of client '
                                      'authentication. Log data can be used to identify, '
                                      'troubleshoot, and repair configuration errors and '
                                      'suboptimal performance.',
                       'entities_results': '',
                       'remediation': 'Azure Console \n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com\n'
                                      " 2. Go to 'Azure Database' for 'PostgreSQL "
                                      "server'\n"
                                      " 3. For each database, click on 'Server "
                                      "parameters'\n"
                                      " 4. Search for 'log_connections'.\n"
                                      " 5. Click 'ON' and save.\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      " Use the below command to update 'log_connections' "
                                      'configuration. \n'
                                      'az postgres server configuration set '
                                      '--resource-group --server-name --name '
                                      'log_connections --value on',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure server parameter 'log_connections' is set to "
                                    "'ON' for PostgreSQL Database Server",
                       'section': '4.14',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.2 Activate audit logging\n'
                              'Ensure that local logging has been enabled on all systems '
                              'and networking devices',
                       'description': "Enable 'log_disconnections' on 'PostgreSQL "
                                      "Servers'. Enabling 'log_disconnections' helps "
                                      "PostgreSQL Database to 'Logs end of a session', "
                                      'including duration, which in turn generates query '
                                      'and error logs. Query and error logs can be used '
                                      'to identify, troubleshoot, and repair '
                                      'configuration errors and sub-optimal performance.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com\n'
                                      " 2. Go to 'Azure Database' for 'PostgreSQL "
                                      "server'\n"
                                      " 3. For each database, click on 'Server "
                                      "parameters'\n"
                                      " 4. Search for 'log_disconnections'.\n"
                                      " 5. Click 'ON' and save.\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      ' Use the below command to update '
                                      "'log_disconnections' configuration. \n"
                                      'az postgres server configuration set '
                                      '--resource-group --server-name --name '
                                      'log_disconnections --value on',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure server parameter 'log_disconnections' is set "
                                    "to 'ON' for PostgreSQL Database Server",
                       'section': '4.15',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.2 Activate audit logging\n'
                              'Ensure that local logging has been enabled on all systems '
                              'and networking devices',
                       'description': "Enable 'log_duration' on 'PostgreSQL Servers'. "
                                      "Enabling 'log_duration' helps the PostgreSQL "
                                      "Database to 'Logs the duration of each completed "
                                      "SQL statement' which in turn generates query and "
                                      'error logs. Query and error logs can be used to '
                                      'identify, troubleshoot, and repair configuration '
                                      'errors and sub-optimal performance.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com\n'
                                      " 2. Go to 'Azure Database' for 'PostgreSQL "
                                      "server'\n"
                                      " 3. For each database, click on 'Server "
                                      "parameters'\n"
                                      " 4. Search for 'log_duration'.\n"
                                      " 5. Click 'ON' and save.\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      " Use the below command to update 'log_duration' "
                                      'configuration. \n'
                                      'az postgres server configuration set '
                                      '--resource-group --server-name --name log_duration '
                                      '--value on',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure server parameter 'log_duration' is set to "
                                    "'ON' for PostgreSQL Database Server",
                       'section': '4.16',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.2 Activate audit logging\n'
                              'Ensure that local logging has been enabled on all systems '
                              'and networking devices',
                       'description': "Enable 'connection_throttling' on 'PostgreSQL "
                                      "Servers'. Enabling 'connection_throttling' helps "
                                      "the PostgreSQL Database to 'Set the verbosity of "
                                      "logged messages' which in turn generates query and "
                                      'error logs with respect to concurrent connections, '
                                      'that could lead to a successful Denial of Service '
                                      '(DoS) attack by exhausting connection resources. A '
                                      'system can also fail or be degraded by an overload '
                                      'of legitimate users. Query and error logs can be '
                                      'used to identify, troubleshoot, and repair '
                                      'configuration errors and sub-optimal performance.',
                       'entities_results': '',
                       'remediation': 'Azure Console \n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com\n'
                                      " 2. Go to 'Azure Database' for 'PostgreSQL "
                                      "server'\n"
                                      " 3. For each database, click on 'Server "
                                      "parameters'\n"
                                      " 4. Search for 'connection_throttling'.\n"
                                      " 5. Click 'ON' and save.\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      ' Use the below command to update '
                                      "'connection_throttling' configuration.\n"
                                      'az postgres server configuration set '
                                      '--resource-group --server-name --name '
                                      'connection_throttling --value on',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure server parameter 'connection_throttling' is "
                                    "set to 'ON' for PostgreSQL Database Server",
                       'section': '4.17',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '6.4 Ensure adequate storage for logs\n'
                              'Ensure that all systems that store logs have adequate '
                              'storage space for the logs generated',
                       'description': "Enable 'log_retention_days' on 'PostgreSQL "
                                      "Servers'. Enabling 'log_retention_days' helps "
                                      "PostgreSQL Database to 'Sets number of days a log "
                                      "file is retained' which in turn generates query "
                                      'and error logs. Query and error logs can be used '
                                      'to identify, troubleshoot, and repair '
                                      'configuration errors and sub-optimal performance.',
                       'entities_results': '',
                       'remediation': 'Azure Console \n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com\n'
                                      " 2. Go to 'Azure Database' for 'PostgreSQL "
                                      "server'\n"
                                      " 3. For each database, click on 'Server "
                                      "parameters'\n"
                                      " 4. Search for 'log_retention_days'.\n"
                                      ' 5. Enter value in range 4-7 (inclusive) and '
                                      'save.\n'
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      'Use the below command to update '
                                      "'log_retention_days' configuration. \n"
                                      'az postgres server configuration set '
                                      '--resource-group --server-name --name '
                                      'log_retention_days --value',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure server parameter 'log_retention_days' is "
                                    'greater than 3 days for PostgreSQL Database Server',
                       'section': '4.18',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Database Services',
                       'cis': '16.2 Configure Centralized Point of Authentication\n'
                              'Configure access for all accounts through as few '
                              'centralized points of authentication as possible, '
                              'including network, security, and cloud systems',
                       'description': 'Use Azure Active Directory Authentication for '
                                      'authentication with SQL Database. Azure Active '
                                      'Directory authentication is a mechanism to connect '
                                      'to Microsoft Azure SQL Database and SQL Data '
                                      'Warehouse by using identities in Azure Active '
                                      'Directory (Azure AD). With Azure AD '
                                      'authentication, identities of database users and '
                                      'other Microsoft services can be managed in one '
                                      'central location. Central ID management provides a '
                                      'single place to manage database users and '
                                      'simplifies permission management.\n'
                                      ' \n'
                                      ' - It provides an alternative to SQL Server '
                                      'authentication.\n'
                                      ' - Helps stop the proliferation of user identities '
                                      'across database servers.\n'
                                      ' - Allows password rotation in a single place.\n'
                                      ' - Customers can manage database permissions using '
                                      'external (AAD) groups.\n'
                                      ' - It can eliminate storing passwords by enabling '
                                      'integrated Windows authentication and other forms '
                                      'of authentication supported by Azure Active '
                                      'Directory.\n'
                                      ' - Azure AD authentication uses contained database '
                                      'users to authenticate identities at the database '
                                      'level.\n'
                                      ' - Azure AD supports token-based authentication '
                                      'for applications connecting to SQL Database.\n'
                                      ' - Azure AD authentication supports ADFS (domain '
                                      'federation) or native user/password authentication '
                                      'for a local Azure Active Directory without domain '
                                      'synchronization.\n'
                                      ' - Azure AD supports connections from SQL Server '
                                      'Management Studio that use Active Directory '
                                      'Universal Authentication, which includes '
                                      'Multi-Factor Authentication (MFA). MFA includes '
                                      'strong authentication with a range of easy '
                                      'verification options: phone call, text message, '
                                      'smart cards with pin, or mobile app notification.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      " 2. For each SQL server, click on 'Active "
                                      "Directory admin'\n"
                                      " 3. Click on 'Set admin'\n"
                                      ' 4. Select an admin\n'
                                      " 5. Click 'Save'\n"
                                      ' \n'
                                      'Azure PowerShell \n'
                                      ' For each Server, set AD Admin \n'
                                      " '''\n"
                                      ' Set-AzureRmSqlServerActiveDirectoryAdministrator '
                                      '-ResourceGroupName -ServerName -DisplayName ""\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Azure Active Directory Admin is '
                                    'configured',
                       'section': '4.19',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Configuring Log Profile',
                       'cis': '6.5 Central Log Management\n'
                              'Ensure that appropriate logs are being aggregated to a '
                              'central log management system for analysis and review',
                       'description': 'Enable log profile for exporting activity logs. A '
                                      'log profile controls how an activity log is '
                                      'exported. By default, activity logs are retained '
                                      'only for 90 days. Log profiles should be defined '
                                      'so that logs can be exported and stored for a '
                                      'longer duration in order to analyze security '
                                      'activities within an Azure subscription.',
                       'entities_results': '',
                       'remediation': 'Azure Console \n'
                                      " 1. Go to 'Activity log'\n"
                                      " 2. Click on 'Export'\n"
                                      ' 3. Configure the setting\n'
                                      " 4. Click on 'Save'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      ' Use the below command to create a Log Profile in '
                                      'Azure Monitoring.\n'
                                      " '''\n"
                                      ' az monitor log-profiles create --categories '
                                      '--days --enabled true --location --locations '
                                      '--name \n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that a Log Profile exists',
                       'section': '5.1.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Configuring Log Profile',
                       'cis': '6.4 Ensure adequate storage for logs\n'
                              'Ensure that all systems that store logs have adequate '
                              'storage space for the logs generated\n'
                              '\n'
                              '6.5 Central Log Management\n'
                              'Ensure that appropriate logs are being aggregated to a '
                              'central log management system for analysis and review',
                       'description': 'Ensure activity log retention is set for 365 days '
                                      'or greater. A log profile controls how the '
                                      'activity log is exported and retained. Since the '
                                      'average time to detect a breach is 210 days, the '
                                      'activity log should be retained for 365 days or '
                                      'more in order to have time to respond to any '
                                      'incidents.',
                       'entities_results': '',
                       'remediation': 'Azure Console \n'
                                      " 1. Go to 'Activity log'\n"
                                      " 2. Select 'Export'\n"
                                      " 3. Set 'Retention (days)' is set to '365' or "
                                      "'0' \n"
                                      " 4. Select 'Save'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      " Use the below command to set the 'Activity log "
                                      "Retention (days)' to '365 or greater'. \n"
                                      " '''\n"
                                      ' az monitor log-profiles update --name --set '
                                      'retentionPolicy.days= '
                                      'retentionPolicy.enabled=true\n'
                                      " '''\n"
                                      ' \n'
                                      ' Use the below command to store logs for forever '
                                      '(indefinitely). \n'
                                      " '''\n"
                                      ' az monitor log-profiles update --name --set '
                                      'retentionPolicy.days=0 '
                                      'retentionPolicy.enabled=false\n'
                                      " ''' \n"
                                      'Note:\n'
                                      ' - If CLI command returns error by expecting '
                                      "location not set to null, append 'location=global' "
                                      'in the command line. When log profile is set using '
                                      'azure portal, by default location is set to null '
                                      'and causes error when tried to update log profile '
                                      'using CLI.',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Retention is set 365 days '
                                    'or greater',
                       'section': '5.1.2',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Configuring Log Profile',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'The log profile should be configured to export all '
                                      'activities from the control/management plane. A '
                                      'log profile controls how the activity log is '
                                      'exported. Configuring the log profile to collect '
                                      'logs for the categories "write", "delete" and '
                                      '"action" ensures that all the control/management '
                                      'plane activities performed on the subscription are '
                                      'exported.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      'On Azure portal there is no provision to check or '
                                      'set categories.\n'
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      " Use command: 'az monitor log-profiles update "
                                      "--name default' in order to update existing "
                                      'default log profile.\n'
                                      '\n'
                                      'Please refer to the documentation: '
                                      "'https://docs.microsoft.com/en-us/cli/azure/monitor/"
                                      "log-profiles?view=azure-cli-latest#az-monitor-log-profiles-update'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure audit profile captures all the activities',
                       'section': '5.1.3',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Configuring Log Profile',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Configure the log profile to export activities '
                                      'from all Azure supported regions/locations '
                                      'including global. A log profile controls how the '
                                      'activity Log is exported. Ensuring that logs are '
                                      'exported from all the Azure supported '
                                      'regions/locations means that logs for potentially '
                                      'unexpected activities occurring in otherwise '
                                      'unused regions are stored and made available for '
                                      'incident response and investigations. Including '
                                      'global region/location in the log profile '
                                      'locations ensures all events from the '
                                      'control/management plane will be exported, as many '
                                      'events in the activity log are global events.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'Activity log'\n"
                                      " 2. Select 'Export'\n"
                                      " 3. Select 'Subscription'\n"
                                      " 4. In 'Regions' dropdown list, check 'Select "
                                      "all' \n"
                                      " 5. Select 'Save'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      " Use command: 'az monitor log-profiles update "
                                      "--name default' in order to update existing "
                                      'default log profile.\n'
                                      ' \n'
                                      'Please refer to the documentation: '
                                      "'https://docs.microsoft.com/en-us/cli/azure/monitor/log-profiles?view=azure-cli-latest#az-monitor-log-profiles-update'",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure the log profile captures activity logs for '
                                    'all regions including global',
                       'section': '5.1.4',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Configuring Log Profile',
                       'cis': '6 Maintenance, Monitoring and Analysis of Audit Logs\n'
                              'Maintenance, Monitoring and Analysis of Audit Logs',
                       'description': 'The storage account container containing the '
                                      'activity log export should not be publicly '
                                      'accessible. Allowing public access to activity log '
                                      'content may aid an adversary in identifying '
                                      "weaknesses in the affected account's use or "
                                      'configuration.',
                       'entities_results': '',
                       'remediation': 'Azure Console \n'
                                      " 1. In right column, Click service 'Storage "
                                      "Accounts' to access Storage account blade\n"
                                      ' 2. Click on the storage account name\n'
                                      " 3. In Section 'Blob Service' click 'Containers'. "
                                      'It will list all the containers in next blade\n'
                                      ' 4. Look for a record with container named as '
                                      "'insight-operational-logs'. Click '...' from right "
                                      "most column to open 'Context menu'\n"
                                      " 5. Click 'Access Policy' from 'Context Menu' and "
                                      "set 'Public Access Level' to 'Private (no "
                                      "anonymous access)'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      " '''\n"
                                      ' az storage container set-permission --name '
                                      'insights-operational-logs --account-name '
                                      '--public-access off\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure the storage container storing the activity '
                                    'logs is not publicly accessible',
                       'section': '5.1.5',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Configuring Log Profile',
                       'cis': '6 Maintenance, Monitoring and Analysis of Audit Logs\n'
                              'Maintenance, Monitoring and Analysis of Audit Logs',
                       'description': 'The storage account with the activity log export '
                                      'container is configured to use BYOK (Use Your Own '
                                      'Key). Configuring the storage account with the '
                                      'activity log export container to use BYOK (Use '
                                      'Your Own Key) provides additional confidentiality '
                                      'controls on log data as a given user must have '
                                      'read permission on the corresponding storage '
                                      'account and must be granted decrypt permission by '
                                      'the CMK.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      "1. In right column, Click service 'Storage "
                                      "Accounts' to access Storage account blade\n"
                                      '2. Click on the storage account name\n'
                                      "3. In Section 'SETTINGS' click 'Encryption'. It "
                                      "will show 'Storage service encryption' "
                                      'configuration pane.\n'
                                      "4. Check 'Use your own key' which will expand "
                                      "'Encryption Key' Settings\n"
                                      "5. Use option 'Enter key URI' or 'Select from Key "
                                      "Vault' to set up encryption with your own key\n"
                                      '\n'
                                      'Azure Command Line Interface 2.0\n'
                                      "'''\n"
                                      'az storage account update --name  '
                                      '--resource-group  '
                                      '--encryption-key-source=Microsoft.Keyvault '
                                      '--encryption-key-vault  --encryption-key-name  '
                                      '--encryption-key-version  \n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure the storage account containing the container '
                                    'with activity logs is encrypted with BYOK (Use Your '
                                    'Own Key)\n',
                       'section': '5.1.6',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Configuring Log Profile',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Enable AuditEvent logging for key vault instances '
                                      'to ensure interactions with key vaults are logged '
                                      'and available. Monitoring how and when key vaults '
                                      'are accessed, and by whom enables an audit trail '
                                      'of interactions with confidential information, '
                                      'keys and certificates managed by Azure Keyvault. '
                                      'Enabling logging for Key Vault saves information '
                                      'in an Azure storage account that the user '
                                      'provides. This creates a new container named '
                                      'insights-logs-auditevent automatically for the '
                                      'specified storage account, and this same storage '
                                      'account can be used for collecting logs for '
                                      'multiple key vaults.',
                       'entities_results': '',
                       'remediation': 'Follow Microsoft Azure documentation and setup '
                                      'Azure Key Vault Logging.',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that logging for Azure KeyVault is 'Enabled'",
                       'section': '5.1.7',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an activity log alert for the Create Policy '
                                      'Assignment event. Monitoring for create policy '
                                      'assignment events gives insight into changes done '
                                      'in "azure policy - assignments" and may reduce the '
                                      'time it takes to detect unsolicited changes.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Create policy assignment'\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//'
                                      'providers/microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": '
                                      '"Microsoft.Authorization/policyAssignments/write",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/'
                                      'actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Alert exists for Create '
                                    'Policy Assignment',
                       'section': '5.2.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an Activity Log Alert for the "Create" or '
                                      '"Update Network Security Group" event. Monitoring '
                                      'for "Create" or "Update Network Security Group" '
                                      'events gives insight into network access changes '
                                      'and may reduce the time it takes to detect '
                                      'suspicious activity.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Create policy assignment'\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//'
                                      'providers/microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": '
                                      '"Microsoft.Authorization/policyAssignments/write",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Alert exists for Create or '
                                    'Update Network Security Group',
                       'section': '5.2.2',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an activity log alert for the Delete '
                                      'Network Security Group event. Monitoring for '
                                      '"Delete Network Security Group" events gives '
                                      'insight into network access changes and may reduce '
                                      'the time it takes to detect suspicious activity.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Delete Network Security Groups' \n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//providers/'
                                      'microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": '
                                      '"Microsoft.Network/networkSecurityGroups/delete",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Alert exists for Delete '
                                    'Network Security Group',
                       'section': '5.2.3',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an activity log alert for the Create or '
                                      'Update Network Security Group Rule event. '
                                      'Monitoring for Create or Update Network Security '
                                      'Group Rule events gives insight into network '
                                      'access changes and may reduce the time it takes to '
                                      'detect suspicious activity.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Create or Update Network Security "
                                      "Groups rule'\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//providers'
                                      '/microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": '
                                      '"Microsoft.Network/networkSecurityGroups/securityRules/write",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Alert exists for Create or '
                                    'Update Network Security Group Rule',
                       'section': '5.2.4',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an activity log alert for the Delete '
                                      'Network Security Group Rule event. Monitoring for '
                                      'Delete Network Security Group Rule events gives '
                                      'insight into network access changes and may reduce '
                                      'the time it takes to detect suspicious activity.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Delete Network Security Groups rule'\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//providers/'
                                      'microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": '
                                      '"Microsoft.Network/networkSecurityGroups/securityRules/delete",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that activity log alert exists for the Delete '
                                    'Network Security Group Rule',
                       'section': '5.2.5',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an activity log alert for the Create or '
                                      'Update Security Solution event. Monitoring for '
                                      'Create or Update Security Solution events gives '
                                      'insight into changes to the active security '
                                      'solutions and may reduce the time it takes to '
                                      'detect suspicious activity.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Create or Update Security Solutions'\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//providers/microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": '
                                      '"Microsoft.Security/securitySolutions/write",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Alert exists for Create or '
                                    'Update Security Solution',
                       'section': '5.2.6',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an activity log alert for the Delete '
                                      'Security Solution event. Monitoring for Delete '
                                      'Security Solution events gives insight into '
                                      'changes to the active security solutions and may '
                                      'reduce the time it takes to detect suspicious '
                                      'activity.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Delete Security Solutions'\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//providers/'
                                      'microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": '
                                      '"Microsoft.Security/securitySolutions/delete",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Alert exists for Delete '
                                    'Security Solution',
                       'section': '5.2.7',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an activity log alert for the Create or '
                                      'Update or Delete SQL Server Firewall Rule event. '
                                      'Monitoring for Create or Update or Delete SQL '
                                      'Server Firewall Rule events gives insight into '
                                      'network access changes and may reduce the time it '
                                      'takes to detect suspicious activity.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Create or Update or Delete SQL Firewall "
                                      "Rule'\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//providers/'
                                      'microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": '
                                      '"Microsoft.Sql/servers/firewallRules/write",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Alert exists for Create or '
                                    'Update or Delete SQL Server Firewall Rule',
                       'section': '5.2.8',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Monitoring using Activity Log Alerts',
                       'cis': '6.3 Enable Detailed Logging\n'
                              'Enable system logging to include detailed information such '
                              'as a event source, date, user, timestamp, source '
                              'addresses, destination addresses, and other useful '
                              'elements',
                       'description': 'Create an activity log alert for the Update '
                                      'Security Policy event. Monitoring for Update '
                                      'Security Policy events gives insight into changes '
                                      'to security policy and may reduce the time it '
                                      'takes to detect suspicious activity.',
                       'entities_results': '',
                       'remediation': 'Azure Command Line Interface 2.0\n'
                                      'Use the below command to create an Activity Log '
                                      "Alert for 'Update or Delete SQL Firewall Rule'\n"
                                      " '''\n"
                                      ' az account get-access-token --query '
                                      '"{subscription:subscription,accessToken:accessToken}" '
                                      "--out tsv | xargs -L1 bash -c 'curl -X PUT -H "
                                      '"Authorization: Bearer $1" -H "Content-Type: '
                                      'application/json" '
                                      'https://management.azure.com/subscriptions/$0/resourceGroups//'
                                      'providers/microsoft.insights/activityLogAlerts/?api-version=2017-04-01 '
                                      '-d@"input.json"\'\n'
                                      " '''\n"
                                      ' \n'
                                      " Where 'input.json' contains the Request body JSON "
                                      'data as mentioned below.\n'
                                      " '''\n"
                                      ' {\n'
                                      '  "location": "Global",\n'
                                      '  "tags": {},\n'
                                      '  "properties": {\n'
                                      '  "scopes": [\n'
                                      '  "/subscriptions/"\n'
                                      '  ],\n'
                                      '  "enabled": true,\n'
                                      '  "condition": {\n'
                                      '  "allOf": [\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Administrative",\n'
                                      '  "field": "category"\n'
                                      '  },\n'
                                      '  {\n'
                                      '  "containsAny": null,\n'
                                      '  "equals": "Microsoft.Security/policies/write",\n'
                                      '  "field": "operationName"\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  "actions": {\n'
                                      '  "actionGroups": [\n'
                                      '  {\n'
                                      '  "actionGroupId": '
                                      '"/subscriptions//resourceGroups//providers/microsoft.insights/actionGroups/",\n'
                                      '  "webhookProperties": null\n'
                                      '  }\n'
                                      '  ]\n'
                                      '  },\n'
                                      '  }\n'
                                      ' }\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Activity Log Alert exists for Update '
                                    'Security Policy',
                       'section': '5.2.9',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Networking',
                       'cis': '9.2 Ensure Only Approved Ports, Protocols and Services Are '
                              'Running\n'
                              'Ensure that only network ports, protocols, and services '
                              'listening on a system with validated business needs, are '
                              'running on each system.',
                       'description': 'Disable RDP access on network security groups from '
                                      'the Internet. The potential security problem with '
                                      'using RDP over the Internet is that attackers can '
                                      'use various brute force techniques to gain access '
                                      'to Azure Virtual Machines. Once the attackers gain '
                                      'access, they can use a virtual machine as a launch '
                                      'point for compromising other machines on an Azure '
                                      'Virtual Network or even attack networked devices '
                                      'outside of Azure.',
                       'entities_results': '',
                       'remediation': 'Disable direct RDP access to your Azure Virtual '
                                      'Machines from the Internet. After direct RDP '
                                      'access from the Internet is disabled, you have '
                                      'other options you can use to access these virtual '
                                      'machines for remote management:\n'
                                      '- Point-to-site VPN\n'
                                      '- Site-to-site VPN \n'
                                      '- ExpressRoute',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that RDP access is restricted from the '
                                    'internet',
                       'section': '6.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Networking',
                       'cis': '9.2 Ensure Only Approved Ports, Protocols and Services Are '
                              'Running\n'
                              'Ensure that only network ports, protocols, and services '
                              'listening on a system with validated business needs, are '
                              'running on each system.',
                       'description': 'Disable SSH access on network security groups from '
                                      'the Internet. The potential security problem with '
                                      'using SSH over the Internet is that attackers can '
                                      'use various brute force techniques to gain access '
                                      'to Azure Virtual Machines. Once the attackers gain '
                                      'access, they can use a virtual machine as a launch '
                                      'point for compromising other machines on the Azure '
                                      'Virtual Network or even attack networked devices '
                                      'outside of Azure.',
                       'entities_results': '',
                       'remediation': 'Disable direct SSH access to your Azure Virtual '
                                      'Machines from the Internet. After direct SSH '
                                      'access from the Internet is disabled, you have '
                                      'other options you can use to access these virtual '
                                      'machines for remote management: \n'
                                      '- Point-to-site VPN\n'
                                      '- Site-to-site VPN \n'
                                      '- ExpressRoute',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that SSH access is restricted from the '
                                    'internet',
                       'section': '6.2',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Networking',
                       'cis': '12 Boundary Defense\nBoundary Defense ',
                       'description': 'Ensure that no SQL Databases allow ingress from '
                                      '0.0.0.0/0 (ANY IP). SQL Server includes a firewall '
                                      'to block access to unauthorized connections. More '
                                      'granular IP addresses can be defined by '
                                      'referencing the range of addresses available from '
                                      'specific datacenters. By default, for a SQL '
                                      'server, a Firewall exists with StartIp of 0.0.0.0 '
                                      'and EndIP of 0.0.0.0 allowing access to all the '
                                      'Azure services. Additionally, a custom rule can be '
                                      'set up with StartIp of 0.0.0.0 and EndIP of '
                                      '255.255.255.255 allowing access from ANY IP over '
                                      'the Internet. In order to reduce the potential '
                                      'attack surface for a SQL server, firewall rules '
                                      'should be defined with more granular IP addresses '
                                      'by referencing the range of addresses available '
                                      'from specific datacenters.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'SQL servers'\n"
                                      ' 2. For each SQL server\n'
                                      " 3. Click on 'Firewall / Virtual Networks'\n"
                                      " 4. Set 'Allow access to Azure services' to 'OFF'\n"
                                      ' 5. Set firewall rules to limit access to only '
                                      'authorized connections\n'
                                      ' \n'
                                      'Azure PowerShell \n'
                                      " Disable Default Firewall Rule 'Allow access to "
                                      "Azure services' :  \n"
                                      " '''Remove-AzureRmSqlServerFirewallRule "
                                      '-FirewallRuleName "AllowAllWindowsAzureIps" '
                                      "-ResourceGroupName -ServerName ''' \n"
                                      ' Remove custom Firewall rule:\n'
                                      " '''Remove-AzureRmSqlServerFirewallRule "
                                      '-FirewallRuleName "" -ResourceGroupName '
                                      "-ServerName ''' \n"
                                      ' Set the appropriate firewall rules: \n'
                                      " '''\n"
                                      ' Set-AzureRmSqlServerFirewallRule '
                                      '-ResourceGroupName -ServerName -FirewallRuleName '
                                      '"" -StartIpAddress "" -EndIpAddress ""\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure no SQL Databases allow ingress 0.0.0.0/0 (ANY '
                                    'IP)',
                       'section': '6.3',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Networking',
                       'cis': '6.4 Ensure adequate storage for logs\n'
                              'Ensure that all systems that store logs have adequate '
                              'storage space for the logs generated. ',
                       'description': 'Network Security Group Flow Logs should be enabled '
                                      'and the retention period is set to greater than or '
                                      'equal to 90 days. Flow logs enable capturing '
                                      'information about IP traffic flowing in and out of '
                                      'network security groups. Logs can be used to check '
                                      'for anomalies and give insight into suspected '
                                      'breaches.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      "1. Go to 'Network Watcher'\n"
                                      "2. Select 'NSG flow logs' blade in the Logs "
                                      'section\n'
                                      '3. Select each Network Security Group from the '
                                      'list\n'
                                      "4. Ensure 'Status' is set to 'On'\n"
                                      "5. Ensure 'Retention (days)' setting 'greater than "
                                      "90 days'\n"
                                      "6. Select your storage account in the 'Storage "
                                      "account' field\n"
                                      "7. Select 'Save'\n"
                                      '\n'
                                      'Azure Command Line Interface 2.0\n'
                                      "Enable the 'NSG flow logs' and set the Retention "
                                      '(days) to greater than or equal to 90 days.\n'
                                      "'''\n"
                                      'az network watcher flow-log configure --nsg  '
                                      '--enabled true --resource-group  --retention 91 '
                                      '--storage-account \n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Network Security Group Flow Log '
                                    "retention period is 'greater than 90 days'",
                       'section': '6.4',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Networking',
                       'cis': '11.2 Document Traffic Configuration Rules\n'
                              'All configuration rules that allow traffic to flow through '
                              'network devices should be documented in a configuration '
                              'management system with a specific business reason for each '
                              'rule, a specific individual’s name responsible for that '
                              'business need, and an expected duration of the need.\n'
                              '\n'
                              '12.1 Maintain an Inventory of Network Boundaries\n'
                              'Maintain an up-to-date inventory of all of the '
                              "organization's network boundaries",
                       'description': 'Enable Network Watcher for Azure subscriptions. '
                                      'Network diagnostic and visualization tools '
                                      'available with Network Watcher help users '
                                      'understand, diagnose, and gain insights to the '
                                      'network in Azure.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'Network Watcher'\n"
                                      ' 2. Right click on the subscription name and click '
                                      "on 'Enable network watcher in all regions'\n"
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      "Configure the 'Network Watcher' for your "
                                      'subscription\n'
                                      "'''\n"
                                      'az network watcher configure --locations --enabled '
                                      '[true] --resource-group --tags key[=value] '
                                      'key[=value]\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that Network Watcher is 'Enabled'",
                       'section': '6.5',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Virtual Machines',
                       'cis': '14.8 Encrypt Sensitive Information at Rest\n'
                              'Encrypt all sensitive information at rest using a tool '
                              'that requires a secondary authentication mechanism not '
                              'integrated into the operating system, in order to access '
                              'the information',
                       'description': 'Ensure that OS disks (boot volumes) are encrypted, '
                                      "where possible. Encrypting the IaaS VM's OS disk "
                                      '(boot volume) ensures that its entire content is '
                                      'fully unrecoverable without a key and thus '
                                      'protects the volume from unwarranted reads.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      'Follow Microsoft Azure documentation.\n'
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      'Use the below command to enable encryption for OS '
                                      'Disk for the specific VM. \n'
                                      "'''\n"
                                      'az vm encryption enable --name --resource-group '
                                      '--volume-type OS --aad-client-id '
                                      '--aad-client-secret --disk-encryption-keyvault '
                                      'https:///secrets//\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'OS disk' are encrypted",
                       'section': '7.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Virtual Machines',
                       'cis': '14.8 Encrypt Sensitive Information at Rest\n'
                              'Encrypt all sensitive information at rest using a tool '
                              'that requires a secondary authentication mechanism not '
                              'integrated into the operating system, in order to access '
                              'the information',
                       'description': 'Ensure that data disks (non-boot volumes) are '
                                      'encrypted, where possible. Encrypting the IaaS '
                                      "VM's Data disks (non-boot volume) ensures that its "
                                      'entire content is fully unrecoverable without a '
                                      'key and thus protects the volume from unwarranted '
                                      'reads.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      'Follow Microsoft Azure documentation.\n'
                                      ' \n'
                                      'Azure Command Line Interface 2.0\n'
                                      'Use the below command to enable encryption for '
                                      'Data Disk for the specific VM.\n'
                                      "'''\n"
                                      'az vm encryption enable --name --resource-group '
                                      '--volume-type DATA --aad-client-id '
                                      '--aad-client-secret --disk-encryption-keyvault '
                                      'https:///secrets//\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Data disks' are encrypted",
                       'section': '7.2',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Virtual Machines',
                       'cis': '14.8 Encrypt Sensitive Information at Rest\n'
                              'Encrypt all sensitive information at rest using a tool '
                              'that requires a secondary authentication mechanism not '
                              'integrated into the operating system, in order to access '
                              'the information',
                       'description': 'Ensure that unattached disks in a subscription are '
                                      "encrypted. Encrypting the IaaS VM's disks ensures "
                                      'that its entire content is fully unrecoverable '
                                      'without a key and thus protects the volume from '
                                      'unwarranted reads. \n'
                                      ' Even if the disk is not attached to any of the '
                                      'VMs, there is always a risk where a compromised '
                                      'user account with administrative access to VM '
                                      'service can mount/attach these data disks which '
                                      'may lead to sensitive information disclosure and '
                                      'tampering.',
                       'entities_results': '',
                       'remediation': 'If data stored in the disk is no longer useful, '
                                      'refer to Azure documentation to delete unattached '
                                      'data disks at:\n'
                                      " '''\n"
                                      ' '
                                      '-https://docs.microsoft.com/en-us/rest/api/compute/disks/delete\n'
                                      ' '
                                      '-https://docs.microsoft.com/en-us/cli/azure/disk?view=azure-cli-l'
                                      'atest#az-disk-delete\n'
                                      " '''\n"
                                      '\n'
                                      ' If data stored in the disk is important, To '
                                      'encrypt the disk refer azure documentation at:\n'
                                      " '''\n"
                                      ' '
                                      '-https://docs.microsoft.com/en-us/rest/api/compute/disks/update#e'
                                      'ncryptionsettings\n'
                                      ' '
                                      '-https://docs.microsoft.com/en-us/cli/azure/disk?view=azure-cli-l'
                                      'atest#az-disk-update\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure that 'Unattached disks' are encrypted",
                       'section': '7.3',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Other Security Considerations',
                       'cis': '16 Account Monitoring and Control\n'
                              'Account Monitoring and Control',
                       'description': 'Ensure that all keys in Azure Key Vault have an '
                                      'expiration time set. Azure Key Vault enables users '
                                      'to store and use cryptographic keys within the '
                                      "Microsoft Azure environment. The 'exp' (expiration "
                                      'time) attribute identifies the expiration time on '
                                      'or after which the key MUST NOT be used for a '
                                      'cryptographic operation. By default, keys never '
                                      'expire. It is thus recommended that keys be '
                                      'rotated in the key vault and set an explicit '
                                      'expiration time for all keys. This ensures that '
                                      'the keys cannot be used beyond their assigned '
                                      'lifetimes.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'Key vaults'\n"
                                      " 2. For each Key vault, click on 'Keys'.\n"
                                      " 3. Under the 'Settings' section, Make sure "
                                      "'Enabled?' is set to Yes\n"
                                      " 4. Set an appropriate 'EXPIRATION DATE' on all "
                                      'keys.\n'
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      "Update the 'EXPIRATION DATE' for the key using "
                                      'below command.\n'
                                      "'''\n"
                                      'az keyvault key set-attributes --name --vault-name '
                                      "--expires Y-m-d'T'H:M:S'Z'\n"
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that the expiration date is set on all keys',
                       'section': '8.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Other Security Considerations',
                       'cis': '16 Account Monitoring and Control\n'
                              'Account Monitoring and Control',
                       'description': 'Ensure that all Secrets in the Azure Key Vault '
                                      'have an expiration time set. The Azure Key Vault '
                                      'enables users to store and keep secrets within the '
                                      'Microsoft Azure environment. Secrets in the Azure '
                                      'Key Vault are octet sequences with a maximum size '
                                      "of 25k bytes each. The 'exp' (expiration time) "
                                      'attribute identifies the expiration time on or '
                                      'after which the secret MUST NOT be used. By '
                                      'default, secrets never expire. It is thus '
                                      'recommended to rotate secrets in the key vault and '
                                      'set an explicit expiration time for all secrets. '
                                      'This ensures that the secrets cannot be used '
                                      'beyond their assigned lifetimes.',
                       'entities_results': '',
                       'remediation': 'Azure Console\n'
                                      " 1. Go to 'Key vaults'\n"
                                      " 2. For each Key vault, click on 'Secrets'.\n"
                                      " 3. Under the 'Settings' section, Make sure "
                                      "'Enabled?' is set to 'Yes'\n"
                                      " 4. Set an appropriate 'EXPIRATION DATE' on all "
                                      'secrets.\n'
                                      ' \n'
                                      'Azure Command Line Interface 2.0 \n'
                                      "Use the below command to set 'EXPIRATION DATE' on "
                                      'the all secrets.\n'
                                      "'''\n"
                                      'az keyvault secret set-attributes --name '
                                      "--vault-name --expires Y-m-d'T'H:M:S'Z'\n"
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that the expiration date is set on all '
                                    'Secrets',
                       'section': '8.2',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Other Security Considerations',
                       'cis': '10 Data Recovery Capabilities\nData Recovery Capabilities',
                       'description': 'The key vault contains object keys, secrets and '
                                      'certificates. Accidental unavailability of a key '
                                      'vault can cause immediate data loss or loss of '
                                      'security functions (authentication, validation, '
                                      'verification, non-repudiation, etc.) supported by '
                                      'the key vault objects. It is recommended the key '
                                      'vault be made recoverable by enabling the "Do Not '
                                      'Purge" and "Soft Delete" functions. This is in '
                                      'order to prevent loss of encrypted data including '
                                      'storage accounts, SQL databases, and/or dependent '
                                      'services provided by key vault objects (Keys, '
                                      'Secrets, Certificates) etc., as may happen in the '
                                      'case of accidental deletion by a user or from '
                                      'disruptive activity by a malicious user. There '
                                      'could be scenarios where users accidently run '
                                      'delete/purge commands on key vault or '
                                      'attacker/malicious user does it deliberately to '
                                      'cause disruption. Deleting or purging a key vault '
                                      'leads to immediate data loss as keys encrypting '
                                      'data and secrets/certificates allowing '
                                      'access/services will become non-accessible. There '
                                      'are 2 key vault properties that plays role in '
                                      'permanent unavailability of a key vault.\n'
                                      " 1> 'enableSoftDelete': \n"
                                      'Setting this parameter to true for a key vault '
                                      'ensures that even if key vault is deleted, Key '
                                      'vault itself or its objects remain recoverable for '
                                      'next 90days. In this span of 90 days either key '
                                      'vault/objects can be recovered or purged '
                                      '(permanent deletion). If no action is taken, after '
                                      '90 days key vault and its objects will be '
                                      'purged. \n'
                                      "2> 'enablePurgeProtection':  \n"
                                      'enableSoftDelete only ensures that key vault is '
                                      'not deleted permanently and will be recoverable '
                                      'for 90 days from date of deletion. However, there '
                                      'are chances that the key vault and/or its objects '
                                      'are accidentally purged and hence will not be '
                                      'recoverable. Setting enablePurgeProtection to '
                                      '"true" ensures that the key vault and its objects '
                                      'cannot be purged. Enabling both the parameters on '
                                      'key vaults ensures that key vaults and their '
                                      'objects cannot be deleted/purged permanently.',
                       'entities_results': '',
                       'remediation': 'To enable "Do Not Purge" and "Soft Delete" for a '
                                      'Key Vault: \n'
                                      'Via Azure Portal\n'
                                      'Azure Portal does not have provision to update the '
                                      'respective configurations\n'
                                      ' \n'
                                      'Via Azure CLI 2.0\n'
                                      " '''\n"
                                      ' az resource update --id '
                                      '/subscriptions/xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups//'
                                      'providers/Microsoft.KeyVault\n'
                                      ' /vaults/ --set '
                                      'properties.enablePurgeProtection=true '
                                      'properties.enableSoftDelete=true\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure the key vault is recoverable',
                       'section': '8.4',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'Other Security Considerations',
                       'cis': '4 Controlled Use of Administrative Privileges\n'
                              'Controlled Use of Administrative Privileges \n'
                              '\n'
                              '14 Controlled Access Based on the Need to Know\n'
                              'Controlled Access Based on the Need to Know',
                       'description': 'Ensure that RBAC is enabled on all Azure '
                                      'Kubernetes Services Instances Azure Kubernetes '
                                      'Services has the capability to integrate Azure '
                                      'Active Directory users and groups into Kubernetes '
                                      'RBAC controls within the AKS Kubernetes API '
                                      'Server. This should be utilized to enable granular '
                                      'access to Kubernetes resources within the AKS '
                                      'clusters supporting RBAC controls not just of the '
                                      'overarching AKS instance but also the individual '
                                      'resources managed within Kubernetes.',
                       'entities_results': '',
                       'remediation': 'WARNING: This setting cannot be changed after AKS '
                                      'deployment, cluster will require recreation.',
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Enable role-based access control (RBAC) within Azure '
                                    'Kubernetes Services',
                       'section': '8.5',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'AppService',
                       'cis': '16 Account Monitoring and Control\n'
                              'Account Monitoring and Control',
                       'description': 'Azure App Service Authentication is a feature that '
                                      'can prevent anonymous HTTP requests from reaching '
                                      'the API app, or authenticate those that have '
                                      'tokens before they reach the API app. If an '
                                      'anonymous request is received from a browser, App '
                                      'Service will redirect to a logon page. To handle '
                                      'the logon process, a choice from a set of identity '
                                      'providers can be made, or a custom authentication '
                                      'mechanism can be implemented. By Enabling App '
                                      'Service Authentication, every incoming HTTP '
                                      'request passes through it before being handled by '
                                      'the application code. It also handles '
                                      'authentication of users with the specified '
                                      'provider(Azure Active Directory, Facebook, Google, '
                                      'Microsoft Account, and Twitter), validation, '
                                      'storing and refreshing of tokens, managing the '
                                      'authenticated sessions and injecting identity '
                                      'information into request headers.',
                       'entities_results': '',
                       'remediation': 'Using Console:\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com \n'
                                      " 2. Go to 'App Services'\n"
                                      ' 3. Click on each App\n'
                                      " 4. Under 'Setting' section, Click on "
                                      "'Authentication / Authorization'\n"
                                      " 5. Set 'App Service Authentication' to 'On'\n"
                                      ' 6. Choose other parameters as per your '
                                      'requirement and Click on Save\n'
                                      ' \n'
                                      'Using Command Line:\n'
                                      ' To set App Service Authentication for an existing '
                                      'app, run the following command:\n'
                                      " '''\n"
                                      ' az webapp auth update --resource-group --name '
                                      '--enabled false\n'
                                      " '''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure App Service Authentication is set on Azure '
                                    'App Service',
                       'section': '9.1',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'AppService',
                       'cis': '7 Email and Web Browser Protections\n'
                              'Email and Web Browser Protections',
                       'description': 'Azure Web Apps allows sites to run under both HTTP '
                                      'and HTTPS by default. Web apps can be accessed by '
                                      'anyone using non-secure HTTP links by default. \n'
                                      ' Non-secure HTTP requests can be restricted and '
                                      'all HTTP requests redirected to the secure HTTPS '
                                      'port. It is recommended to enforce HTTPS-only '
                                      'traffic. Enabling HTTPS-only traffic will redirect '
                                      'all non-secure HTTP request to HTTPS ports. HTTPS '
                                      'uses the SSL/TLS protocol to provide a secure '
                                      'connection, which is both encrypted and '
                                      'authenticated. So it is important to support HTTPS '
                                      'for the security benefits.',
                       'entities_results': '',
                       'remediation': 'Using Console:\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com \n'
                                      " 2. Go to 'App Services'\n"
                                      ' 3. Click on each App\n'
                                      " 4. Under 'Setting' section, Click on 'SSL "
                                      "settings'\n"
                                      " 5. Set 'HTTPS Only' to 'On' under 'Protocol "
                                      "Settings' section\n"
                                      ' \n'
                                      'Using Command Line:\n'
                                      'To set HTTPS-only traffic value for an existing '
                                      'app, run the following command:\n'
                                      "'''\n"
                                      'az webapp update --resource-group --name --set '
                                      'httpsOnly=false\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure web app redirects all HTTP traffic to HTTPS '
                                    'in Azure App Service',
                       'section': '9.2',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'AppService',
                       'cis': '7 Email and Web Browser Protections\n'
                              'Email and Web Browser Protections',
                       'description': 'The TLS(Transport Layer Security) protocol secures '
                                      'transmission of data over the internet using '
                                      'standard encryption technology. Encryption should '
                                      'be set with the latest version of TLS. App service '
                                      'allows TLS 1.2 by default, which is the '
                                      'recommended TLS level by industry standards, such '
                                      'as PCI DSS. App service currently allows the web '
                                      'app to set TLS versions 1.0, 1.1 and 1.2. It is '
                                      'highly recommended to use the latest TLS 1.2 '
                                      'version for web app secure connections.',
                       'entities_results': '',
                       'remediation': 'Using Console:\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com \n'
                                      " 2. Go to 'App Services'\n"
                                      ' 3. Click on each App\n'
                                      " 4. Under 'Setting' section, Click on 'SSL "
                                      "settings'\n"
                                      " 5. Set 'Minimum TLS Version' to '1.2' under "
                                      "'Protocol Settings' section\n"
                                      ' \n'
                                      'Using Command Line:\n'
                                      'To set TLS Version for an existing app, run the '
                                      'following command:\n'
                                      "'''\n"
                                      'az webapp config set --resource-group --name '
                                      '--min-tls-version 1.2\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure web app is using the latest version of TLS '
                                    'encryption',
                       'section': '9.3',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'AppService',
                       'cis': '14 Controlled Access Based on the Need to Know\n'
                              'Controlled Access Based on the Need to Know',
                       'description': 'Client certificates allow for the app to request a '
                                      'certificate for incoming requests. Only clients '
                                      'that have a valid certificate will be able to '
                                      'reach the app. The TLS mutual authentication '
                                      'technique in enterprise environments ensures the '
                                      'authenticity of clients to the server. If incoming '
                                      'client certificates are enabled, then only an '
                                      'authenticated client who has valid certificates '
                                      'can access the app.',
                       'entities_results': '',
                       'remediation': 'Using Console:\n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com \n'
                                      " 2. Go to 'App Services'\n"
                                      ' 3. Click on each App\n'
                                      " 4. Under 'Setting' section, Click on 'SSL "
                                      "settings'\n"
                                      " 5. Set 'Incoming client certificates' to 'On' "
                                      "under 'Protocol Settings' section\n"
                                      ' \n'
                                      'Using Command Line:\n'
                                      'To set Incoming client certificates value for an '
                                      'existing app, run the following command:\n'
                                      "'''\n"
                                      'az webapp update --resource-group --name --set '
                                      'clientCertEnabled=true\n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': "Ensure the web app has 'Client Certificates "
                                    "(Incoming client certificates)' set to 'On'",
                       'section': '9.4',
                       'status': 'Passed'},
                      {'account': '',
                       'affected_entities': 0,
                       'category': 'AppService',
                       'cis': '16.2 Configure Centralized Point of Authentication\n'
                              'Configure access for all accounts through as few '
                              'centralized points of authentication as possible, '
                              'including network, security, and cloud systems',
                       'description': 'Managed service identity in App Service makes the '
                                      'app more secure by eliminating secrets from the '
                                      'app, such as credentials in the connection '
                                      'strings. When registering with Azure Active '
                                      'Directory in the app service, the app will connect '
                                      'to other Azure services securely without the need '
                                      'of username and passwords. App Service provides a '
                                      'highly scalable, self-patching web hosting service '
                                      'in Azure. It also provides a managed identity for '
                                      'apps, which is a turn-key solution for securing '
                                      'access to Azure SQL Database and other Azure '
                                      'services.',
                       'entities_results': '',
                       'remediation': 'Using Console: \n'
                                      ' 1. Login to Azure Portal using '
                                      'https://portal.azure.com \n'
                                      " 2. Go to 'App Services'\n"
                                      ' 3. Click on each App\n'
                                      " 4. Under 'Setting' section, Click on 'Identity'\n"
                                      " 5. Set 'Status' to 'On'\n"
                                      ' \n'
                                      'Using Command Line:\n'
                                      'To set Register with Azure Active Directory '
                                      'feature for an existing app, run the following '
                                      'command:\n'
                                      "'''\n"
                                      'az webapp identity assign --resource-group '
                                      '--name \n'
                                      "'''",
                       'results': {'checked': 0, 'failed': 0},
                       'rule_name': 'Ensure that Register with Azure Active Directory is '
                                    'enabled on App Service',
                       'section': '9.5',
                       'status': 'Passed'}],
            'status': 'ok'}
