def get_cis_aws_compliance_report():
    return {
        'status': 'ok',
        'rules': [
            {
                'status': 'Passed',
                'section': '1.1',
                'rule_name': 'Avoid the use of the "Root" Account',
                'category': 'Identity and Access Management',
                'results': {
                    'failed': 0,
                    'checked': 3,
                },
                'affected_entities': 0,
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
                '''.strip(),
                'entities_results': 'The use of the "Root" account is avoided.',
                'cis': '4.3 Ensure the Use of Dedicated Administrative Accounts.\nEnsure that all users with '
                       'administrative account access use a dedicated or secondary account for elevated activities. '
                       'This account should only be used for administrative activities and not '
                       'internet browsing, email, or similar activities.'
            },
            {
                'status': 'Failed',
                'section': '1.2',
                'rule_name': 'Ensure multi-factor authentication (MFA) is enabled for all IAM users that have a '
                             'console password',
                'category': 'Identity and Access Management',
                'results': {
                    'failed': 1,
                    'checked': 3,
                },
                'affected_entities': 4,
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
                    '''.strip(),
                'entities_results': 'IAM Users which do not have multi-factor authentication (MFA):\nUser: user1',
                'entities_results_query': {
                    'type': 'users',
                    'query': '((adapters_data.aws_adapter.id == ({"$exists":true,"$ne":""}))) '
                             'and not (((adapters_data.aws_adapter.user_associated_mfa_devices == '
                             '({"$exists":true,"$ne":[]})) and '
                             'adapters_data.aws_adapter.user_associated_mfa_devices != []))'
                },
                'cis': '4.5 Use Multifactor Authentication For All Administrative Access\n'
                       'Use multi-factor authentication and encrypted channels for all administrative account access. '
            },
            {
                'status': 'No Data',
                'error': 'An error occurred (AuthFailure) when calling the DescribeInstances operation: AWS was not '
                         'able to validate the provided access credentials',
                'section': '1.3',
                'rule_name': 'Ensure credentials unused for 90 days or greater are disabled',
                'category': 'Identity and Access Management',
                'results': {
                    'failed': 0,
                    'checked': 0,
                },
                'affected_entities': 0,
                'description': 'AWS IAM users can access AWS resources using different types of credentials, '
                               'such as passwords or access keys. It is recommended that all credentials that have '
                               'been unused in 90 or greater days be removed or deactivated. Disabling or removing '
                               'unnecessary credentials will reduce the window of opportunity for credentials '
                               'associated with a compromised or abandoned account to be used. ',
                'remediation': '''
After you identify the inactive accounts or unused credentials, use the following steps to disable them:
1. Sign in to the AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.
2. In the navigation pane, choose Users.
3. In the User Name list, choose the user with credentials over 90 days old.
4. Choose the Security Credentials tab, and then choose Make inactive. 
                                '''.strip(),
                'cis': '16.9 Disable Dormant Accounts'
                       'Automatically disable dormant accounts after a set period of inactivity. '
            }
        ]
    }


def get_compliance(compliance_name: str, method: str):
    if compliance_name == 'CIS_AWS':
        if method == 'report':
            return get_cis_aws_compliance_report()
        if method == 'report_no_data':
            return {
                'status': 'no_data',
                'error': 'Please connect the AWS Adapter',
                'rules': [],
            }

    raise ValueError(f'Data not found')
