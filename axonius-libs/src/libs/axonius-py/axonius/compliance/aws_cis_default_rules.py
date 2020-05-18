def get_default_cis_aws_compliance_report():
    return {
        'status': 'ok', 'rules': [
            {
                'status': 'Passed', 'section': '1.1', 'rule_name': 'Avoid the use of the "root" Account',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'The "root" account has unrestricted access to all resources in the AWS account. '
                               'It is highly recommended that the use of this account be avoided. The "root" account '
                               'is the most privileged AWS account. Minimizing the use of this account and adopting '
                               'the principle of least privilege for access management will reduce the risk of '
                               'accidental changes and unintended disclosure of highly privileged credentials.',
                'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for "Root" account usage and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name `<cloudtrail_log_group_name>` -filter-name `<root_usage_metric>` --metric-transformations metricName= `<root_usage_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filterpattern '{ $.userIdentity.type = "Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType != "AwsServiceEvent" }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<root_usage_alarm>`  --metricname  `<root_usage_metric>`  --statistic Sum --period 300 --threshold 1 -comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 -namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                '''.strip(), 'entities_results': '',
                'cis': '4.3 Ensure the Use of Dedicated Administrative Accounts.\nEnsure that all users with '
                       'administrative account access use a dedicated or secondary account for elevated activities. '
                       'This account should only be used for administrative activities and not '
                       'internet browsing, email, or similar activities.'}, {
                'status': 'Passed', 'section': '1.2',
                'rule_name': 'Ensure multi-factor authentication (MFA) is enabled for all IAM users that have a '
                             'console password', 'category': 'Identity and Access Management', 'account': '',
                'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Multi-Factor Authentication (MFA) adds an extra layer of protection on top of a user '
                               'name and password. With MFA enabled, when a user signs in to an AWS website, '
                               'they will be prompted for their user name and password as well as for an '
                               'authentication code from their AWS MFA device. It is recommended that MFA be enabled '
                               'for all accounts that have a console password. Enabling MFA provides increased '
                               'security for console access as it requires the authenticating principal to possess '
                               'a device that emits a time-sensitive key and have knowledge of a credential.',
                'remediation': '''
Perform the following to enable MFA:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. In the navigation pane, choose Users.
3. In the User Name list, choose the name of the intended MFA user.
4. Choose the Security Credentials tab, and then choose Manage MFA Device.
5. Follow the Manage MFA Device wizard to assign the type of device appropriate for your environment.
                    '''.strip(), 'entities_results': '',
                'cis': '4.5 Use Multifactor Authentication For All Administrative Access\n'
                       'Use multi-factor authentication and encrypted channels for all administrative account access. '},
            {
                'status': 'Passed',
                'error': 'An error occurred (AuthFailure) when calling the DescribeInstances operation: AWS was not '
                         'able to validate the provided access credentials', 'section': '1.3',
                'rule_name': 'Ensure credentials unused for 90 days or greater are disabled',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'AWS IAM users can access AWS resources using different types of credentials, '
                               'such as passwords or access keys. It is recommended that all credentials that have '
                               'been unused in 90 or greater days be removed or deactivated. Disabling or removing '
                               'unnecessary credentials will reduce the window of opportunity for credentials '
                               'associated with a compromised or abandoned account to be used. ', 'remediation': '''
After you identify the inactive accounts or unused credentials, use the following steps to disable them:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. In the navigation pane, choose Users.
3. In the User Name list, choose the user with credentials over 90 days old.
4. Choose the Security Credentials tab, and then choose Make inactive.
                                '''.strip(), 'cis': '16.9 Disable Dormant Accounts\n'
                                                    'Automatically disable dormant accounts after a set period of inactivity. '},
            {
                'status': 'Passed', 'section': '1.4',
                'rule_name': 'Ensure access keys are rotated every 90 days or less',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Access keys consist of an access key ID and secret access key, which are used to sign '
                               'programmatic requests that you make to AWS. AWS users need their own access keys to '
                               'make programmatic calls to AWS from the AWS Command Line Interface (AWS CLI), Tools '
                               'for Windows PowerShell, the AWS SDKs, or direct HTTP calls using the APIs for '
                               'individual AWS services. It is recommended that all access keys be regularly rotated. '
                               'Rotating access keys will reduce the window of opportunity for an access key that is '
                               'associated with a compromised or terminated account to be used. Access keys should be '
                               'rotated to ensure that data cannot be accessed with an old key which might have been '
                               'lost, cracked, or stolen.', 'remediation': '''
Perform the following to rotate access keys:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. In the navigation pane, choose Users.
3. In the User Name list, choose the user with access keys older than 90 days.
4. Choose the Security Credentials tab, and then choose Make inactive.
5. Choose Create access key
6. Update all applications with the new Access Key credentials
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '1.5',
                'rule_name': 'Ensure IAM password policy requires at least one uppercase letter',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Password policies are, in part, used to enforce password complexity requirements. IAM '
                               'password policies can be used to ensure password are comprised of different character '
                               'sets. It is recommended that the password policy require at least one uppercase '
                               'letter. Setting a password complexity policy increases account resiliency against '
                               'brute force login attempts.', 'remediation': '''
Perform the following to set the password policy as prescribed:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. Click on Account Settings on the Left Pane
3. Check "Requires at least one uppercase letter"
4. Click "Apply password policy"
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '1.6',
                'rule_name': 'Ensure IAM password policy requires at least one lowercase letter',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Password policies are, in part, used to enforce password complexity requirements. '
                               'IAM password policies can be used to ensure password are comprised of different '
                               'character sets. It is recommended that the password policy require at least one '
                               'lowercase letter. Setting a password complexity policy increases account resiliency '
                               'against brute force login attempts.', 'remediation': '''
Perform the following to set the password policy as prescribed:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. Click on Account Settings on the Left Pane
3. Check "Requires at least one lowercase letter"
4. Click "Apply password policy"
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '1.7',
                'rule_name': 'Ensure IAM password policy requires at least one symbol',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Password policies are, in part, used to enforce password complexity requirements. '
                               'IAM password policies can be used to ensure password are comprised of different '
                               'character sets. It is recommended that the password policy require at least one '
                               'symbol. Setting a password complexity policy increases account resiliency against '
                               'brute force login attempts.', 'remediation': '''
Perform the following to set the password policy as prescribed:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. Click on Account Settings on the Left Pane
3. Check "Require at least one non-alphanumeric character"
4. Click "Apply password policy"
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '1.8',
                'rule_name': 'Ensure IAM password policy requires at least one number',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Password policies are, in part, used to enforce password complexity requirements. '
                               'IAM password policies can be used to ensure password are comprised of different '
                               'character sets. It is recommended that the password policy require at least one '
                               'number. Setting a password complexity policy increases account resiliency against '
                               'brute force login attempts.', 'remediation': '''
Perform the following to set the password policy as prescribed:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. Click on Account Settings on the Left Pane
3. Check "Require at least one number"
4. Click "Apply password policy"
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '1.9',
                'rule_name': 'Ensure IAM password policy requires a minimum length of 14 or greater',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Password policies are, in part, used to enforce password complexity requirements. '
                               'IAM password policies can be used to ensure password are at least a given length. It '
                               'is recommended that the password policy require a minimum password length 14. Setting '
                               'a password complexity policy increases account resiliency against brute force login '
                               'attempts.', 'remediation': '''
Perform the following to set the password policy as prescribed:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. Click on Account Settings on the Left Pane
3. Set "Minimum password length" to 14 or greater.
4. Click "Apply password policy"
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '1.10',
                'rule_name': 'Ensure IAM password policy prevents password reuse',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'IAM password policies can prevent the reuse of a given password by the same user. It '
                               'is recommended that the password policy prevent the reuse of passwords. Preventing '
                               'password reuse increases account resiliency against brute force login attempts.',
                'remediation': '''
Perform the following to set the password policy as prescribed:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. Click on Account Settings on the Left Pane
3. Check "Prevent password reuse"
4. Set "Number of passwords to remember" to 24
5. Click "Apply password policy"
                    '''.strip(), 'entities_results': '',
                'cis': '4.4 Use Unique Passwords\nWhere multi-factor authentication is not supported (such as local '
                       'administrator, root, or service accounts), accounts will use passwords that are unique to '
                       'that system.'}, {
                'status': 'Passed', 'section': '1.11',
                'rule_name': 'Ensure IAM password policy expires passwords within 90 days or less',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'IAM password policies can require passwords to be rotated or expired after a given '
                               'number of days. It is recommended that the password policy expire passwords after 90 '
                               'days or less. Reducing the password lifetime increases account resiliency against '
                               'brute force login attempts. Additionally, requiring regular password changes help in '
                               'the following scenarios:\n- Passwords can be stolen or compromised sometimes without '
                               'your knowledge. This can happen via a system compromise, software vulnerability, or '
                               'internal threat.\n- Certain corporate and government web filters or proxy servers '
                               'have the ability to intercept and record traffic even if it\'s encrypted.\n- Many '
                               'people use the same password for many systems such as work, email, and personal.\n'
                               '- Compromised end user workstations might have a keystroke logger.', 'remediation': '''
Perform the following to set the password policy as prescribed:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. Click on Account Settings on the Left Pane
3. Check "Enable password expiration"
4. Set "Password expiration period (in days):" to 90 or less
5. Click "Apply password policy"
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '1.12', 'rule_name': 'Ensure no root account access key exists',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'The root account is the most privileged user in an AWS account. AWS Access Keys '
                               'provide programmatic access to a given AWS account. It is recommended that all access '
                               'keys associated with the root account be removed. Removing access keys associated with '
                               'the root account limits vectors by which the account can be compromised. Additionally, '
                               'removing the root access keys encourages the creation and use of role based accounts '
                               'that are least privileged.', 'remediation': '''
Perform the following to delete or disable active root access keys being used:
1. Sign in to the AWS Management Console as Root and open the IAM console at https://console.aws.amazon.com/iam/.
2. Click on <Root_Account_Name> at the top right and select Security Credentials from the drop down list
3. On the pop out screen Click on Continue to Security Credentials
4. Click on Access Keys (Access Key ID and Secret Access Key)
5. Under the Status column if there are any Keys which are Active, do one of the following:
- Click on Make Inactive - (Temporarily disable Key - may be needed again)
- Click Delete - (Deleted keys cannot be recovered)
                    '''.strip(), 'entities_results': '',
                'cis': '4.3 Ensure the Use of Dedicated Administrative Accounts.\nEnsure that all users with '
                       'administrative account access use a dedicated or secondary account for elevated activities. '
                       'This account should only be used for administrative activities and not '
                       'internet browsing, email, or similar activities.'}, {
                'status': 'Passed', 'section': '1.13', 'rule_name': 'Ensure MFA is enabled for the "root" account',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'The root account is the most privileged user in an AWS account. MFA adds an extra '
                               'layer of protection on top of a user name and password. With MFA enabled, when a user '
                               'signs in to an AWS website, they will be prompted for their user name and password as '
                               'well as for an authentication code from their AWS MFA device. Enabling MFA provides '
                               'increased security for console access as it requires the authenticating principal to '
                               'possess a device that emits a time-sensitive key and have knowledge of a credential. '
                               'When virtual MFA is used for root accounts, it is recommended that the device used is '
                               'NOT a personal device, but rather a dedicated mobile device (tablet or phone) that is '
                               'managed to be kept charged and secured independent of any individual personal devices. '
                               '("non-personal virtual MFA") This lessens the risks of losing access to the MFA due to '
                               'device loss, device trade-in or if the individual owning the device is no longer '
                               'employed at the company.', 'remediation': '''
Perform the following to establish MFA for the root account:
1. Sign in to the AWS Management Console as Root and open the IAM console at https://console.aws.amazon.com/iam/.
2. Choose Dashboard , and under Security Status , expand Activate MFA on your root account.
3. Choose Activate MFA
4. Follow the Manage MFA Device wizard to assign the type of device appropriate for your environment.
                    '''.strip(), 'entities_results': '',
                'cis': '4.5 Use Multifactor Authentication For All Administrative Access\nUse multi-factor '
                       'authentication and encrypted channels for all administrative account access.'}, {
                'status': 'Passed', 'section': '1.14',
                'rule_name': 'Ensure hardware MFA is enabled for the "root" account',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'The root account is the most privileged user in an AWS account. MFA adds an extra '
                               'layer of protection on top of a user name and password. With MFA enabled, when a user '
                               'signs in to an AWS website, they will be prompted for their user name and password as '
                               'well as for an authentication code from their AWS MFA device. For Level 2, it is '
                               'recommended that the root account be protected with a hardware MFA. A hardware MFA has '
                               'a smaller attack surface than a virtual MFA. For example, a hardware MFA does not '
                               'suffer the attack surface introduced by the mobile smartphone on which a virtual MFA '
                               'resides. Using hardware MFA for many AWS accounts may create a logistical device '
                               'management issue. If this is the case, consider implementing this Level 2 '
                               'recommendation selectively to the highest security AWS accounts and the Level 1 '
                               'recommendation applied to the remaining accounts. Link to order AWS compatible '
                               'hardware MFA device: http://onlinenoram.gemalto.com/ ', 'remediation': '''
Perform the following to establish MFA for the root account:
1. Sign in to the AWS Management Console as Root and open the IAM console at https://console.aws.amazon.com/iam/.
2. Choose Dashboard , and under Security Status , expand Activate MFA on your root account.
3. Choose Activate MFA
4. Follow the Manage MFA Device wizard to assign a hardware-based (not virtual) device for your environment.
                    '''.strip(), 'entities_results': '',
                'cis': '4.5 Use Multifactor Authentication For All Administrative Access\nUse multi-factor '
                       'authentication and encrypted channels for all administrative account access. '}, {
                'status': 'Passed', 'section': '1.16',
                'rule_name': 'Ensure IAM policies are attached only to groups or roles',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'By default, IAM users, groups, and roles have no access to AWS resources. IAM policies '
                               'are the means by which privileges are granted to users, groups, or roles. It is '
                               'recommended that IAM policies be applied directly to groups and roles but not users. '
                               'Assigning privileges at the group or role level reduces the complexity of access '
                               'management as the number of users grow. Reducing access management complexity may '
                               'in-turn reduce opportunity for a principal to inadvertently receive or retain '
                               'excessive privileges. ', 'remediation': '''
Perform the following to create an IAM group, assign the policy to the group, and then add the users to the group. The policy is applied to each user in the group.
To create an IAM group:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. In the navigation pane, click Groups and then click Create New Group.
3. In the Group Name box, type the name of the group and then click Next Step .
4. In the list of policies, select the check box for each policy that you want to apply to all members of the group. Then click Next Step.
5. Click Create Group

To add a user to a given group:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. In the navigation pane, click Groups
3. Select the group to add a user to and click Add Users To Group
4. Select the users to be added to the group and Click Add Users

To remove direct association between a user and a policy:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. In the left navigation pane, click on Users
3. For each user:
       - Select the user
       - Click on the Permissions tab
       - Expand Managed Policies
       - Click Detach Policy for each policy
       - Expand Inline Policies
       - Click Remove Policy for each policy
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '1.20',
                'rule_name': 'Ensure a support role has been created to manage incidents with AWS Support',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'AWS provides a support center that can be used for incident notification and response, '
                               'as well as technical support and customer services. Create an IAM Role to allow '
                               'authorized users to manage incidents with AWS Support. By implementing least privilege '
                               'for access control, an IAM Role will require an appropriate IAM Policy to allow '
                               'Support Center Access in order to manage Incidents with AWS Support.', 'remediation': '''
    Using the Amazon unified command line interface:
    - Create an IAM role for managing incidents with AWS:
    1. Create a trust relationship policy document that allows <iam_user> to manage AWS incidents, and save it locally as /tmp/TrustPolicy.json:
    {"Version": "2012-10-17","Statement": [{"Effect": "Allow","Principal": {"AWS": "<span style="font-style: italic;"><iam_user></span>"},"Action": "sts:AssumeRole"}]}
    2. Create the IAM role using the above trust policy:
    aws iam create-role --role-name <aws_support_iam_role> --assume-role-policy-document file:///tmp/TrustPolicy.json
    3. Attach 'AWSSupportAccess' managed policy to the created IAM role:
    aws iam attach-role-policy --policy-arn <iam_policy_arn> --role-name <aws_support_iam_role>
                        '''.strip(), 'entities_results': '', 'cis': ''}, {
                'status': 'Passed', 'section': '1.22',
                'rule_name': 'Ensure IAM policies that allow full "*:*" administrative privileges are not created',
                'category': 'Identity and Access Management', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'IAM policies are the means by which privileges are granted to users, groups, or roles. '
                               'It is recommended and considered a standard security advice to grant least '
                               'privilege-that is, granting only the permissions required to perform a task. Determine '
                               'what users need to do and then craft policies for them that let the users perform only '
                               'those tasks, instead of allowing full administrative privileges. It\'s more secure '
                               'to start with a minimum set of permissions and grant additional permissions as '
                               'necessary, rather than starting with permissions that are too lenient and then trying '
                               'to tighten them later.\n'
                               'Providing full administrative privileges instead of restricting '
                               'to the minimum set of permissions '
                               'that the user is required to do exposes the resources '
                               'to potentially unwanted actions. IAM policies that have a statement with "Effect": '
                               '"Allow" with "Action": "*" over "Resource": "*" should be removed.', 'remediation': '''
Perform the following to detach the policy that has full administrative privileges:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. In the navigation pane, click Policies and then search for the policy name found in the audit step.
3. Select the policy that needs to be deleted.
4. In the policy action menu, select first Detach
5. Select all Users, Groups, Roles that have this policy attached
6. Click Detach Policy
7. In the policy action menu, select Detach
                    '''.strip(), 'entities_results': '',
                'cis': '4 Controlled Use of Administrative Privileges\nControlled Use of Administrative Privileges'}, {
                'status': 'Passed', 'section': '2.1', 'rule_name': 'Ensure CloudTrail is enabled in all Regions',
                'category': 'Logging', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'AWS CloudTrail is a web service that records AWS API calls for your account and '
                               'delivers log files to you. The recorded information includes the identity of the API '
                               'caller, the time of the API call, the source IP address of the API caller, the request '
                               'parameters, and the response elements returned by the AWS service. CloudTrail provides '
                               'a history of AWS API calls for an account, including API calls made via the Management '
                               'Console, SDKs, command line tools, and higher-level AWS services (such as '
                               'CloudFormation).\nThe AWS API call history produced by CloudTrail enables security '
                               'analysis, resource change tracking, and compliance auditing. Additionally\n- Ensuring '
                               'that a multi-regions trail exists will ensure that unexpected activity occurring in '
                               'otherwise unused regions is detected\n- Ensuring that a multi-regions trail exists '
                               'will ensure that Global Service Logging is enabled for a trail by default to capture '
                               'recording of events generated on AWS global services\n- For a multi-regions trail, '
                               'ensuring that management events configured for all type of Read/Writes ensures '
                               'recording of management operations that are performed on all resources in an AWS '
                               'account', 'remediation': '''
Perform the following to enable global (Multi-region) CloudTrail logging:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/cloudtrail
2. Click on Trails on the left navigation pane
3. Click Get Started Now , if presented
4. Click Add new trail
5. Enter a trail name in the Trail name box
6. Set the Apply trail to all regions option to Yes
7. Specify an S3 bucket name in the S3 bucket box
8. Click Create
9. If one or more trails already exist, select the target trail to enable for global logging
10. Click the edit icon (pencil) next to Apply trail to all regions , Click Yes and Click Save.
11. Click the edit icon (pencil) next to Management Events click All for setting Read/Write Events and Click Save.
                    '''.strip(), 'entities_results': '',
                'cis': '6.2 Activate audit logging\nEnsure that local logging has been enabled on all systems and '
                       'networking devices. '}, {
                'status': 'Passed', 'section': '2.2', 'rule_name': 'Ensure CloudTrail log file validation is enabled',
                'category': 'Logging', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'CloudTrail log file validation creates a digitally signed digest file containing a '
                               'hash of each log that CloudTrail writes to S3. These digest files can be used to '
                               'determine whether a log file was changed, deleted, or unchanged after CloudTrail '
                               'delivered the log. It is recommended that file validation be enabled on all '
                               'CloudTrails. Enabling log file validation will provide additional integrity checking '
                               'of CloudTrail logs.', 'remediation': '''
Perform the following to enable log file validation on a given trail:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/cloudtrail
2. Click on Trails on the left navigation pane
3. Click on target trail
4. Within the S3 section click on the edit icon (pencil)
5. Click Advanced
6. Click on the Yes radio button in section Enable log file validation
7. Click Save
                    '''.strip(), 'entities_results': '',
                'cis': '6 Maintenance, Monitoring and Analysis of Audit Logs\nMaintenance, Monitoring and Analysis of '
                       'Audit Logs'}, {
                'status': 'Passed', 'section': '2.3',
                'rule_name': 'Ensure the S3 bucket CloudTrail logs to is not publicly accessible',
                'category': 'Logging', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'CloudTrail logs a record of every API call made in your AWS account. These logs file '
                               'are stored in an S3 bucket. It is recommended that the bucket policy, or access '
                               'control list (ACL), applied to the S3 bucket that CloudTrail logs to prevents public '
                               'access to the CloudTrail logs. Allowing public access to CloudTrail log content may '
                               'aid an adversary in identifying weaknesses in the affected account\'s use or '
                               'configuration.', 'remediation': '''
Perform the following to remove any public access that has been granted to the bucket via an ACL or S3 bucket policy:
1. Go to Amazon S3 console at https://console.aws.amazon.com/s3/home
2. Right-click on the bucket and click Properties
3. In the Properties pane, click the Permissions tab.
4. The tab shows a list of grants, one row per grant, in the bucket ACL. Each row identifies the grantee and the permissions granted.
5. Select the row that grants permission to Everyone or Any Authenticated User
6. Uncheck all the permissions granted to Everyone or Any Authenticated User (click x to delete the row).
7. Click Save to save the ACL.
8. If the Edit bucket policy button is present, click it.
9. Remove any Statement having an Effect set to Allow and a Principal set to "*" or {"AWS" : "*"}.
                    '''.strip(), 'entities_results': '',
                'cis': '14.6 Protect Information through Access Control Lists\nProtect all information stored on '
                       'systems with file system, network share, claims, application, or database specific access '
                       'control lists. These controls will enforce the principle that only authorized individuals '
                       'should have access to the information based on their need to access the information as a part '
                       'of their responsibilities.'}, {
                'status': 'Passed', 'section': '2.4',
                'rule_name': 'Ensure CloudTrail trails are integrated with Amazon CloudWatch Logs',
                'category': 'Logging', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'AWS CloudTrail is a web service that records AWS API calls made in a given AWS '
                               'account. The recorded information includes the identity of the API caller, the time of '
                               'the API call, the source IP address of the API caller, the request parameters, and the '
                               'response elements returned by the AWS service. CloudTrail uses Amazon S3 for log file '
                               'storage and delivery, so log files are stored durably. In addition to capturing '
                               'CloudTrail logs within a specified S3 bucket for long term analysis, realtime analysis '
                               'can be performed by configuring CloudTrail to send logs to CloudWatch Logs. For a '
                               'trail that is enabled in all regions in an account, CloudTrail sends log files from '
                               'all those regions to a CloudWatch Logs log group. It is recommended that CloudTrail '
                               'logs be sent to CloudWatch Logs. The intent of this recommendation is to ensure AWS '
                               'account activity is being captured, monitored, and appropriately alarmed on. '
                               'CloudWatch Logs is a native way to accomplish this using AWS services but does not '
                               'preclude the use of an alternate solution. Sending CloudTrail logs to CloudWatch Logs '
                               'will facilitate real-time and historic activity logging based on user, API, resource, '
                               'and IP address, and provides opportunity to establish alarms and notifications for '
                               'anomalous or sensitivity account activity.', 'remediation': '''
Perform the following to establish the prescribed state:
1. Sign in to the AWS Management Console and open the CloudTrail console at https://console.aws.amazon.com/cloudtrail/
2. Under All Buckets, click on the target bucket you wish to evaluate
3. Click Properties on the top right of the console
4. Click Trails in the left menu
5. Click on each trail where no CloudWatch Logs are defined
6. Go to the CloudWatch Logs section and click on Configure
7. Define a new or select an existing log group and click on Continue
8. Configure IAM Role which will deliver CloudTrail events to CloudWatch Logs
9. Create/Select an IAM Role and Policy Name and then click Allow to continue
                    '''.strip(), 'entities_results': '',
                'cis': '6.2 Activate audit logging\nEnsure that local logging has been enabled on all systems and '
                       'networking devices.\n6.5 Central Log Management\nEnsure that appropriate logs are being '
                       'aggregated to a central log management system for analysis and review.'}, {
                'status': 'Passed', 'section': '2.5', 'rule_name': 'Ensure AWS Config is enabled in all regions',
                'category': 'Logging', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'AWS Config is a web service that performs configuration management of supported AWS '
                               'resources within your account and delivers log files to you. The recorded information '
                               'includes the configuration item (AWS resource), relationships between configuration '
                               'items (AWS resources), any configuration changes between resources. It is recommended '
                               'to enable AWS Config be enabled in all regions. The AWS configuration item history '
                               'captured by AWS Config enables security analysis, resource change tracking, and '
                               'compliance auditing. ', 'remediation': '''
To implement AWS Config configuration: Via AWS Management Console:
1. Select the region you want to focus on in the top right of the console
2. Click Services
3. Click Config
4. Define which resources you want to record in the selected region
5. Choose to include global resources (IAM resources)
6. Specify an S3 bucket in the same account or in another managed AWS account
7. Create an SNS Topic from the same AWS account or another managed AWS account
                    '''.strip(), 'entities_results': '',
                'cis': '1.4 Maintain Detailed Asset Inventory\nMaintain an accurate and up-to-date inventory of all '
                       'technology assets with the potential to store or process information. This inventory shall '
                       'include all hardware assets, whether connected to the organization\'s network or '
                       'not.\n11.2 Document Traffic Configuration Rules\nAll configuration rules that allow traffic to '
                       'flow through network devices should be documented in a configuration management system with a '
                       'specific business reason for each rule, a specific individual\'s name responsible for that '
                       'business need, and an expected duration of the need.\n16.1 Maintain an Inventory of '
                       'Authentication Systems\nMaintain an inventory of each of the organization\'s authentication '
                       'systems, including those located onsite or at a remote service provider.'}, {
                'status': 'Passed', 'section': '2.6',
                'rule_name': 'Ensure S3 bucket access logging is enabled on the CloudTrail S3 bucket',
                'category': 'Logging', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'S3 Bucket Access Logging generates a log that contains access records for each request '
                               'made to your S3 bucket. An access log record contains details about the request, such '
                               'as the request type, the resources specified in the request worked, and the time and '
                               'date the request was processed. It is recommended that bucket access logging be '
                               'enabled on the CloudTrail S3 bucket. By enabling S3 bucket logging on target S3 '
                               'buckets, it is possible to capture all events which may affect objects within an '
                               'target buckets. Configuring logs to be placed in a separate bucket allows access to '
                               'log information which can be useful in security and incident response workflows.',
                'remediation': '''
Perform the following to enable S3 bucket logging:
1. Sign in to the AWS Management Console and open the S3 console at https://console.aws.amazon.com/s3.
2. Under All Buckets click on the target S3 bucket
3. Click on Properties in the top right of the console
4. Under Bucket: <s3_bucket_for_cloudtrail> click on Logging
5. Configure bucket logging: Click on Enabled checkbox, then select Target Bucket from list and Enter a Target Prefix
6. Click Save
                    '''.strip(), 'entities_results': '',
                'cis': '6.2 Activate audit logging\nEnsure that local logging has been enabled on all systems and '
                       'networking devices.\n 14.9 Enforce Detail Logging for Access or Changes to Sensitive '
                       'Data\nEnforce detailed audit logging for access to sensitive data or changes to sensitive '
                       'data (utilizing tools such as File Integrity Monitoring or Security Information and Event '
                       'Monitoring). '}, {
                'status': 'Passed', 'section': '2.7',
                'rule_name': 'Ensure CloudTrail logs are encrypted at rest using AWS KMS CMKs', 'category': 'Logging',
                'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'AWS CloudTrail is a web service that records AWS API calls for an account and makes '
                               'those logs available to users and resources in accordance with IAM policies. AWS Key '
                               'Management Service (KMS) is a managed service that helps create and control the '
                               'encryption keys used to encrypt account data, and uses Hardware Security Modules '
                               '(HSMs) to protect the security of encryption keys. CloudTrail logs can be configured '
                               'to leverage server side encryption (SSE) and KMS customer created master keys (CMK) '
                               'to further protect CloudTrail logs. It is recommended that CloudTrail be configured '
                               'to use SSE-KMS. Configuring CloudTrail to use SSE-KMS provides additional '
                               'confidentiality controls on log data as a given user must have S3 read permission on '
                               'the corresponding log bucket and must be granted decrypt permission by the CMK policy.',
                'remediation': '''
Perform the following to configure CloudTrail to use SSE-KMS:
1. Sign in to the AWS Management Console and open the CloudTrail console at https://console.aws.amazon.com/cloudtrail
2. In the left navigation pane, choose Trails .
3. Click on a Trail
4. Under the S3 section click on the edit button (pencil icon)
5. Click Advanced
6. Select an existing CMK from the KMS key Id drop-down menu.
Note: Ensure the CMK is located in the same region as the S3 bucket
Note: You will need to apply a KMS Key policy on the selected CMK in order for CloudTrail as a service to encrypt and decrypt log files using the CMK provided.
7. Click Save
                    '''.strip(), 'entities_results': '',
                'cis': '6 Maintenance, Monitoring and Analysis of Audit Logs\nMaintenance, Monitoring and Analysis of '
                       'Audit Logs'}, {
                'status': 'Passed', 'section': '2.8',
                'rule_name': 'Ensure rotation for customer-created CMKs is enabled', 'category': 'Logging',
                'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'AWS Key Management Service (KMS) allows customers to rotate the backing key which is '
                               'key material stored within the KMS which is tied to the key ID of the Customer Created '
                               'customer master key (CMK). It is the backing key that is used to perform cryptographic '
                               'operations such as encryption and decryption. Automated key rotation currently retains '
                               'all prior backing keys so that decryption of encrypted data can take place '
                               'transparently. It is recommended that CMK key rotation be enabled. Rotating encryption '
                               'keys helps reduce the potential impact of a compromised key as data encrypted with a '
                               'new key cannot be accessed with a previous key that may have been exposed.',
                'remediation': '''
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam.
2. In the left navigation pane, choose Encryption Keys.
3. Select a customer created master key (CMK)
4. Under the Key Policy section, move down to Key Rotation.
5. Check the Rotate this key every year checkbox.
                    '''.strip(), 'entities_results': '',
                'cis': '6 Maintenance, Monitoring and Analysis of Audit Logs\nMaintenance, Monitoring and Analysis of '
                       'Audit Logs'}, {
                'status': 'Passed', 'section': '2.9', 'rule_name': 'Ensure VPC flow logging is enabled in all VPCs',
                'category': 'Logging', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'VPC Flow Logs is a feature that enables you to capture information about the IP '
                               'traffic going to and from network interfaces in your VPC. After you\'ve created a '
                               'flow log, you can view and retrieve its data in Amazon CloudWatch Logs. It is '
                               'recommended that VPC Flow Logs be enabled for packet "Rejects" for VPCs. VPC Flow Logs '
                               'provide visibility into network traffic that traverses the VPC and can be used to '
                               'detect anomalous traffic or insight during security workflows.', 'remediation': '''
Perform the following to determine if VPC Flow logs is enabled:
1. Sign in to the AWS Management Console and open Amazon VPC console at https://console.aws.amazon.com/vpc/
2. In the left navigation pane, select Your VPCs
3. Select a VPC
4. In the right pane, select the Flow Logs tab.
5. If no Flow Log exists, click Create Flow Log
6. For Filter, select Reject
7. Enter in a Role and Destination Log Group
8. Click Create Log Flow
9. Click on CloudWatch Logs Group
                    '''.strip(), 'entities_results': '', 'cis': '6.2 Activate audit logging\n'
                                                                'Ensure that local logging has been enabled on all systems and '
                                                                'networking devices.\n12.5 Configure Monitoring Systems to Record Network Packets\nConfigure '
                                                                'monitoring systems to record network packets passing through the boundary at each of the '
                                                                'organization\'s network boundaries.'}, {
                'status': 'Passed', 'section': '3.1',
                'rule_name': 'Ensure a log metric filter and alarm exist for unauthorized API calls',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for unauthorized API calls. '
                               'Monitoring unauthorized API calls will help reveal application errors and may reduce '
                               'time to detect malicious activity. ', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for unauthorized API calls and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<unauthorized_api_calls_metric>`  --metric-transformations metricName= `<unauthorized_api_calls_metric>`
,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{ ($.errorCode = "*UnauthorizedOperation") || ($.errorCode = "AccessDenied*") }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<unauthorized_api_calls_alarm>`  --metric-name  `<unauthorized_api_calls_metric>`  --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 -namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '6.5 Central Log Management\nEnsure that appropriate logs are being aggregated to a central '
                       'log management system for analysis and review.\n 6.7 Regularly Review Logs\nOn a regular '
                       'basis, review logs to identify anomalies or abnormal events.'}, {
                'status': 'Passed', 'section': '3.2',
                'rule_name': 'Ensure a log metric filter and alarm exist for AWS Management Console sign-in without '
                             'MFA', 'category': 'Monitoring', 'account': '', 'results': {
                                 'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for console logins that are '
                               'not protected by multi-factor authentication (MFA). Monitoring for single-factor '
                               'console logins will increase visibility into accounts that are not protected by MFA.',
                'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for AWS Management Console sign-in without MFA and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<no_mfa_console_signin_metric>`  --metric-transformations metricName= `<no_mfa_console_signin_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{ ($.eventName = "ConsoleLogin") && ($.additionalEventData.MFAUsed != "Yes") }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<no_mfa_console_signin_alarm>`  --metric-name  `<no_mfa_console_signin_metric>`  --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold -evaluation-periods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '3.3',
                'rule_name': 'Ensure a log metric filter and alarm exist for usage of "root" account',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for root login attempts. '
                               'Monitoring for root account logins will provide visibility into the use of a fully '
                               'privileged account and an opportunity to reduce the use of it.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for "Root" account usage and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name `<cloudtrail_log_group_name>` -filter-name `<root_usage_metric>` --metric-transformations metricName= `<root_usage_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filterpattern '{ $.userIdentity.type = "Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType != "AwsServiceEvent" }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<root_usage_alarm>`  --metricname  `<root_usage_metric>`  --statistic Sum --period 300 --threshold 1 -comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 -namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '4.9 Log and Alert on Unsuccessful Administrative Account Login\nConfigure systems to issue a '
                       'log entry and alert on unsuccessful logins to an administrative account.'}, {
                'status': 'Passed', 'section': '3.4',
                'rule_name': 'Ensure a log metric filter and alarm exist for IAM policy changes',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for changes made to Identity '
                               'and Access Management (IAM) policies. Monitoring changes to IAM policies will help '
                               'ensure authentication and authorization controls remain intact.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for IAM policy changes and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name `<cloudtrail_log_group_name>` -filter-name  `<iam_changes_metric>`  --metric-transformations metricName= `<iam_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 -filter-pattern '{($.eventName=DeleteGroupPolicy)||($.eventName=DeleteRolePolicy) ||($.eventName=DeleteUserPolicy) ||($.eventName=PutGroupPolicy) ||($.eventName=PutRolePolicy)|| ($.eventName=PutUserPolicy)|| ($.eventName=CreatePolicy)||($.eventName=DeletePolicy)||($.eventName=CreatePolicyVersion)||($.eventName=DeletePolicyVersion)||($.eventName=AttachRolePolicy)||($.eventName=DetachRolePolicy)||($.eventName=AttachUserPolicy)||($.eventName=DetachUserPolicy)||($.eventName=AttachGroupPolicy)||($.eventName=DetachGroupPolicy)}'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<iam_changes_alarm>`  -metric-name  `<iam_changes_metric>`  --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '3.5',
                'rule_name': 'Ensure a log metric filter and alarm exist for CloudTrail configuration changes',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for detecting changes to '
                               'CloudTrail\'s configurations. Monitoring changes to CloudTrail\'s configuration '
                               'will help ensure sustained visibility to activities performed in the AWS account.',
                'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for cloudtrail configuration changes and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name `<cloudtrail_cfg_changes_metric>`  --metric-transformations metricName= `<cloudtrail_cfg_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{ ($.eventName = CreateTrail) || ($.eventName = UpdateTrail) || ($.eventName = DeleteTrail) || ($.eventName = StartLogging) || ($.eventName = StopLogging) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<cloudtrail_cfg_changes_alarm>`  --metric-name  `<cloudtrail_cfg_changes_metric>`  --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 -namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '6 Maintenance, Monitoring and Analysis of Audit Logs\nMaintenance, Monitoring and Analysis of '
                       'Audit Logs'}, {
                'status': 'Passed', 'section': '3.6', 'rule_name': 'Ensure a log metric filter and alarm exist for '
                                                                   'AWS Management Console authentication failures',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for failed console '
                               'authentication attempts. Monitoring failed console logins may decrease lead time to '
                               'detect an attempt to brute force a credential, which may provide an indicator, such '
                               'as source IP, that can be used in other event correlation.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for AWS management Console Login Failures and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name `<console_signin_failure_metric>`  --metric-transformations metricName= `<console_signin_failure_metric>`
,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{ ($.eventName = ConsoleLogin) && ($.errorMessage = "Failed authentication") }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<console_signin_failure_alarm>`  --metric-name  `<console_signin_failure_metric>`  --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 -namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '3.7', 'rule_name': 'Ensure a log metric filter and alarm exist for '
                                                                   'disabling or scheduled deletion of customer created CMKs',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for customer created CMKs '
                               'which have changed state to disabled or scheduled deletion. Data encrypted with '
                               'disabled or deleted keys will no longer be accessible.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for disabled or scheduled for deletion CMK's and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<s3_bucket_policy_changes_metric>`  --metric-transformations metricName= `<s3_bucket_policy_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{ ($.eventSource = s3.amazonaws.com) && (($.eventName = PutBucketAcl) || ($.eventName = PutBucketPolicy) || ($.eventName = PutBucketCors) || ($.eventName = PutBucketLifecycle) || ($.eventName = PutBucketReplication) || ($.eventName = DeleteBucketPolicy) || ($.eventName = DeleteBucketCors) || ($.eventName = DeleteBucketLifecycle) || ($.eventName = DeleteBucketReplication)) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<s3_bucket_policy_changes_alarm>`  --metric-name  `<s3_bucket_policy_changes_metric>`  --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '16 Account Monitoring and Control\nAccount Monitoring and Control'}, {
                'status': 'Passed', 'section': '3.8',
                'rule_name': 'Ensure a log metric filter and alarm exist for S3 bucket policy changes',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for changes to S3 bucket '
                               'policies. Monitoring changes to S3 bucket policies may reduce time to detect and '
                               'correct permissive policies on sensitive S3 buckets.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for disabled or scheduled for deletion CMK's and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<disable_or_delete_cmk_changes_metric>`  --metrictransformations metricName= `<disable_or_delete_cmk_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern
'{($.eventSource = kms.amazonaws.com) && (($.eventName=DisableKey)||($.eventName=ScheduleKeyDeletion)) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<disable_or_delete_cmk_changes_alarm>`  --metric-name  `<disable_or_delete_cmk_changes_metric>`  --statistic Sum --period 300 -threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluationperiods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '6.2 Activate audit logging\nEnsure that local logging has been enabled on all systems and '
                       'networking devices.\n14 Controlled Access Based on the Need to Know\nControlled Access Based '
                       'on the Need to Know '}, {
                'status': 'Passed', 'section': '3.9',
                'rule_name': 'Ensure a log metric filter and alarm exist for AWS Config configuration changes',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'recommended that a metric filter and alarm be established for detecting changes to '
                               'CloudTrail\'s configurations. Monitoring changes to AWS Config configuration will '
                               'help ensure sustained visibility of configuration items within the AWS account.',
                'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for AWS Configuration changes and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<aws_config_changes_metric>`  --metric-transformations metricName= `<aws_config_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{ ($.eventSource = config.amazonaws.com) && (($.eventName=StopConfigurationRecorder)||($.eventName=DeleteDeliveryChannel) ||($.eventName=PutDeliveryChannel)||($.eventName=PutConfigurationRecorder)) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<aws_config_changes_alarm>`  -metric-name  `<aws_config_changes_metric>`  --statistic Sum --period 300 -threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluationperiods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '1.4 Maintain Detailed Asset Inventory\nMaintain an accurate and up-to-date inventory of all '
                       'technology assets with the potential to store or '
                       'process information. This inventory shall include '
                       'all hardware assets,'
                       ' whether connected to the organization\'s network or not.\n11.2 Document '
                       'Traffic Configuration Rules\n'
                       'All configuration rules that allow traffic to flow through network '
                       'devices should be documented in a configuration '
                       'management system with a specific business reason '
                       'for each rule, a specific individual\'s '
                       'name responsible for that business need, and an expected '
                       'duration of the need.\n16.1 Maintain an Inventory of Authentication Systems\n'
                       'Maintain an inventory '
                       'of each of the organization\'s authentication systems, '
                       'including those located onsite or at a '
                       'remote service provider.'}, {
                'status': 'Passed', 'section': '3.10',
                'rule_name': 'Ensure a log metric filter and alarm exist for security group changes',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. Security '
                               'Groups are a stateful packet filter that controls ingress and egress traffic within a '
                               'VPC. It is recommended that a metric filter and alarm be established changes to '
                               'Security Groups. Monitoring changes to security group will help ensure that resources '
                               'and services are not unintentionally exposed.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for security groups changes and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<security_group_changes_metric>`  --metric-transformations metricName= `<security_group_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{
($.eventName = AuthorizeSecurityGroupIngress) || ($.eventName = AuthorizeSecurityGroupEgress) || ($.eventName = RevokeSecurityGroupIngress) || ($.eventName = RevokeSecurityGroupEgress) || ($.eventName = CreateSecurityGroup) || ($.eventName = DeleteSecurityGroup) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<security_group_changes_alarm>`  --metric-name  `<security_group_changes_metric>`  --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 -namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '4.8 Log and Alert on Changes to Administrative Group Membership\n Configure systems to issue a '
                       'log entry and alert when an account is added to or removed from any group assigned '
                       'administrative privileges.'}, {
                'status': 'Passed', 'section': '3.11', 'rule_name': 'Ensure a log metric filter and alarm exist for '
                                                                    'changes to Network Access Control Lists (NACL)',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. NACLs are '
                               'used as a stateless packet filter to control ingress and egress traffic for subnets '
                               'within a VPC. It is recommended that a metric filter and alarm be established for '
                               'changes made to NACLs. Monitoring changes to NACLs will help ensure that AWS resources '
                               'and services are not unintentionally exposed.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for NACL changes and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<nacl_changes_metric>`  --metric-transformations metricName= `<nacl_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 -filter-pattern '{ ($.eventName = CreateNetworkAcl) || ($.eventName = CreateNetworkAclEntry) || ($.eventName = DeleteNetworkAcl) || ($.eventName = DeleteNetworkAclEntry) || ($.eventName = ReplaceNetworkAclEntry) || ($.eventName = ReplaceNetworkAclAssociation) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<nacl_changes_alarm>`  -metric-name  `<nacl_changes_metric>`  --statistic Sum --period 300 -threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluationperiods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '11.3 Use Automated Tools to Verify Standard Device Configurations and Detect Changes\nCompare '
                       'all network device configuration against approved security configurations defined for each '
                       'network device in use and alert when any deviations are discovered.'}, {
                'status': 'Passed', 'section': '3.12',
                'rule_name': 'Ensure a log metric filter and alarm exist for changes to network gateways',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. Network '
                               'gateways are required to send/receive traffic to a destination outside of a VPC. It is '
                               'recommended that a metric filter and alarm be established for changes to network '
                               'gateways. Monitoring changes to network gateways will help ensure that all '
                               'ingress/egress traffic traverses the VPC border via a controlled path.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for network gateways changes and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<network_gw_changes_metric>`  --metric-transformations metricName= `<network_gw_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{
($.eventName = CreateCustomerGateway) || ($.eventName = DeleteCustomerGateway) || ($.eventName = AttachInternetGateway) || ($.eventName = CreateInternetGateway) || ($.eventName = DeleteInternetGateway) || ($.eventName = DetachInternetGateway) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<network_gw_changes_alarm>`  -metric-name  `<network_gw_changes_metric>`  --statistic Sum --period 300 -threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluationperiods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '6.2 Activate audit logging\nEnsure that local logging has been enabled on all systems and '
                       'networking devices.\n11.3 Use Automated Tools to Verify Standard Device Configurations and '
                       'Detect Changes\nCompare all network device configuration against approved security '
                       'configurations defined for each network device in use and alert when any deviations are '
                       'discovered.'}, {
                'status': 'Passed', 'section': '3.13',
                'rule_name': 'Ensure a log metric filter and alarm exist for route table changes',
                'category': 'Monitoring', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. Routing '
                               'tables are used to route network traffic between subnets and to network gateways. It '
                               'is recommended that a metric filter and alarm be established for changes to route '
                               'tables. Monitoring changes to route tables will help ensure that all VPC traffic flows '
                               'through an expected path.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for route table changes and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<route_table_changes_metric>`  --metric-transformations metricName= `<route_table_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 --filter-pattern '{
($.eventName = CreateRoute) || ($.eventName = CreateRouteTable) || ($.eventName = ReplaceRoute) || ($.eventName = ReplaceRouteTableAssociation) || ($.eventName = DeleteRouteTable) || ($.eventName = DeleteRoute) || ($.eventName = DisassociateRouteTable) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<route_table_changes_alarm>`  --metric-name  `<route_table_changes_metric>`  --statistic Sum --period 300 -threshold 1 --comparison-operator GreaterThanOrEqualToThreshold -evaluation-periods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '6.2 Activate audit logging\nEnsure that local logging has been enabled on all systems and '
                       'networking devices.\n11.3 Use Automated Tools to Verify Standard Device Configurations and '
                       'Detect Changes\nCompare all network device configuration against approved security '
                       'configurations defined for each network device in use and alert when any deviations are '
                       'discovered.'}, {
                'status': 'Passed', 'section': '3.14',
                'rule_name': 'Ensure a log metric filter and alarm exist for VPC changes', 'category': 'Monitoring',
                'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Real-time monitoring of API calls can be achieved by directing CloudTrail Logs to '
                               'CloudWatch Logs and establishing corresponding metric filters and alarms. It is '
                               'possible to have more than 1 VPC within an account, in addition it is also possible to '
                               'create a peer connection between 2 VPCs enabling network traffic to route between '
                               'VPCs. It is recommended that a metric filter and alarm be established for changes made '
                               'to VPCs. Monitoring changes to IAM policies will help ensure authentication and '
                               'authorization controls remain intact.', 'remediation': '''
Perform the following to setup the metric filter, alarm, SNS topic, and subscription:
1. Identify the log group name configured for use with active multi-region CloudTrail
2. Create a metric filter based on filter pattern provided which checks for VPC changes and the <cloudtrail_log_group_name> taken from audit step 1.
aws logs put-metric-filter --log-group-name <cloudtrail_log_group_name> -filter-name  `<vpc_changes_metric>`  --metric-transformations metricName= `<vpc_changes_metric>` ,metricNamespace='CISBenchmark',metricValue=1 -filter-pattern '{ ($.eventName = CreateVpc) || ($.eventName = DeleteVpc) || ($.eventName = ModifyVpcAttribute) || ($.eventName = AcceptVpcPeeringConnection) || ($.eventName = CreateVpcPeeringConnection) || ($.eventName = DeleteVpcPeeringConnection) || ($.eventName = RejectVpcPeeringConnection) || ($.eventName = AttachClassicLinkVpc) || ($.eventName = DetachClassicLinkVpc) || ($.eventName = DisableVpcClassicLink) || ($.eventName = EnableVpcClassicLink) }'
3. Create an SNS topic that the alarm will notify
aws sns create-topic --name <sns_topic_name>
4. Create an SNS subscription to the topic created in step 3
aws sns subscribe --topic-arn <sns_topic_arn> --protocol <protocol_for_sns> -notification-endpoint <sns_subscription_endpoints>
5. Create an alarm that is associated with the CloudWatch Logs Metric Filter created in step 2 and an SNS topic created in step 3
aws cloudwatch put-metric-alarm --alarm-name  `<vpc_changes_alarm>`  -metric-name  `<vpc_changes_metric>`  --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1 --namespace 'CISBenchmark' --alarm-actions <sns_topic_arn>
                    '''.strip(), 'entities_results': '',
                'cis': '5.5 Implement Automated Configuration Monitoring Systems\nUtilize a Security Content '
                       'Automation Protocol (SCAP) compliant configuration monitoring system to verify all security '
                       'configuration elements, catalog approved exceptions, and alert when unauthorized changes '
                       'occur.'}, {
                'status': 'Passed', 'section': '4.1',
                'rule_name': 'Ensure no security groups allow ingress from 0.0.0.0/0 to port 22',
                'category': 'Networking', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Security groups provide stateful filtering of ingress/egress network traffic to AWS '
                               'resources. It is recommended that no security group allows unrestricted ingress access '
                               'to port 22. Removing unfettered connectivity to remote console services, such as SSH, '
                               'reduces a server\'s exposure to risk.', 'remediation': '''
Perform the following to implement the prescribed state:
1. Login to the AWS Management Console at https://console.aws.amazon.com/vpc/home
2. In the left pane, click Security Groups
3. For each security group, perform the following:
4. Select the security group
5. Click the Inbound Rules tab
6. Identify the rules to be removed
7. Click the x in the Remove column
8. Click Save
                    '''.strip(), 'entities_results': '',
                'cis': '9.2 Ensure Only Approved Ports, Protocols and Services Are Running\nEnsure that only network '
                       'ports, protocols, and services listening on a system with validated business needs, are '
                       'running on each system.'}, {
                'status': 'Passed', 'section': '4.2',
                'rule_name': 'Ensure no security groups allow ingress from 0.0.0.0/0 to port 3389',
                'category': 'Networking', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'Security groups provide stateful filtering of ingress/egress network traffic to AWS '
                               'resources. It is recommended that no security group allows unrestricted ingress access '
                               'to port 3389. Removing unfettered connectivity to remote console services, such as '
                               'RDP, reduces a server\'s exposure to risk.', 'remediation': '''
Perform the following to implement the prescribed state:
1. Login to the AWS Management Console at https://console.aws.amazon.com/vpc/home
2. In the left pane, click Security Groups
3. For each security group, perform the following:
4. Select the security group
5. Click the Inbound Rules tab
6. Identify the rules to be removed
7. Click the x in the Remove column
8. Click Save
                    '''.strip(), 'entities_results': '',
                'cis': '9.2 Ensure Only Approved Ports, Protocols and Services Are Running\nEnsure that only network '
                       'ports, protocols, and services listening on a system with validated business needs, are '
                       'running on each system.'}, {
                'status': 'Passed', 'section': '4.3',
                'rule_name': 'Ensure the default security group of every VPC restricts all traffic',
                'category': 'Networking', 'account': '', 'results': {
                    'failed': 0, 'checked': 0, }, 'affected_entities': 0,
                'description': 'A VPC comes with a default security group whose initial settings deny all inbound '
                               'traffic, allow all outbound traffic, and allow all traffic between instances assigned '
                               'to the security group. If you don\'t specify a security group when you launch an '
                               'instance, the instance is automatically assigned to this default security group. '
                               'Security groups provide stateful filtering of ingress/egress network traffic to AWS '
                               'resources. It is recommended that the default security group restrict all traffic. The '
                               'default VPC in every region should have its default security group updated to comply. '
                               'Any newly created VPCs will automatically contain a default security group that will '
                               'need remediation to comply with this recommendation. Configuring all VPC default '
                               'security groups to restrict all traffic will encourage least privilege security group '
                               'development and mindful placement of AWS resources into security groups which will '
                               'in-turn reduce the exposure of those resources.', 'remediation': '''
Perform the following to implement the prescribed state:
1. Identify AWS resources that exist within the default security group
2. Create a set of least privilege security groups for those resources
3. Place the resources in those security groups
4. Remove the resources noted in #1 from the default security group
Security Group State
1. Login to the AWS Management Console at https://console.aws.amazon.com/vpc/home
2. Repeat the next steps for all VPCs - including the default VPC in each AWS region:
3. In the left pane, click Security Groups
4. For each default security group, perform the following:
5. Select the default security group
6. Click the Inbound Rules tab
7. Remove any inbound rules
8. Click the Outbound Rules tab
9. Remove any inbound rules
                    '''.strip(), 'entities_results': '',
                'cis': '14.6 Protect Information through Access Control Lists\nProtect all information stored on '
                       'systems with file system, network share, claims, application, or database specific access '
                       'control lists. These controls will enforce the principle that only authorized individuals '
                       'should have access to the information based on their need to access the information as a part '
                       'of their responsibilities.'}]}
