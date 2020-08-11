EKS_YAML_FILE = 'apiVersion: v1\nclusters:\n- cluster:\n    server: {endpoint}\n    certificate-authority-data:' + \
                ' {ca_cert}\n  name: kubernetes\ncontexts:\n- context:\n' + \
                '    cluster: kubernetes\n    user: aws\n  name: aws\ncurrent-context: aws\n' + \
                'kind: Config\npreferences: {preferences}\nusers:\n- name: aws\n  user:\n    exec:\n' + \
                '      apiVersion: client.authentication.k8s.io/v1alpha1\n      command: aws-iam-authenticator\n' + \
                '      args:\n        - \"token\"\n        - \"-i\"\n        - \"{cluster_name}\"'

ELASTICSEARCH_DOMAIN_LIMIT = 5

# this regex can be used to match and extract data from an aws arn
# group 1 is the partition (aws | aws-cn | aws-us-gov | etc.)
# group 2 is the service identifier (s3, cloudfront, ec2, etc.)
# group 3 is the region (us-east-1, etc.)
# group 4 is the account number (12 digits)
# group 5 is the resource id/type (can be : or / separated)
# group 6 is the path or wildcard
ARN_PATTERN = r'^arn:(aws.*):(.*):(.*-.*-\d*|):(\d{12}):([a-zA-Z0-9-_]*)[\/|:](.*)'

FORWARDED_COOKIES = ['none', 'whitelist', 'all']
VIEWER_PROTOCOL_POLICY = ['allow-all', 'https-only', 'redirect-to-https']
PROTOCOL_POLICY = ['http-only', 'match-viewer', 'https-only']
SSL_SUPPORT_METHOD = ['sni-only', 'vip']
MINIMUM_PROTOCOL_VERSION = ['SSLv3', 'TLSv1', 'TLSv1_2016', 'TLSv1.1_2016', 'TLSv1.2_2018']
CERTIFICATE_SOURCE = ['cloudfront', 'iam', 'acm']
CLOUDFRONT_RESTRICTION_TYPE = ['blacklist', 'whitelist', 'none']
PRICE_CLASS = ['PriceClass_100', 'PriceClass_200', 'PriceClass_All']
HTTP_VERSION = ['http1.1', 'http2']
ALIAS_RECORDALS_STATUS = ['APPROVED', 'SUSPENDED', 'PENDING']

# s3
BUCKET_ACL = ['private', 'public-read', 'public-read-write', 'authenticated-read']
OBJECT_ACL = ['private', 'public-read', 'public-read-write', 'authenticated-read',
              'aws-exec-read', 'bucket-owner-read', 'bucket-owner-full-control']
OBJECT_STORAGE_CLASS = ['STANDARD', 'REDUCED_REDUNDANCY', 'STANDARD_IA',
                        'ONEZONE_IA', 'INTELLIGENT_TIERING', 'GLACIER', 'DEEP_ARCHIVE']
SERVER_SIDE_ENCRYPTION = ['AES256', 'aws:kms']

# configuration schema items
ADAPTER_NAME = 'aws_adapter'
AWS_ACCESS_KEY_ID_NAME = 'aws_access_key_id'
AWS_SECRET_ACCESS_KEY_NAME = 'aws_secret_access_key'
AWS_USE_IAM = 'aws_use_iam'
AWS_S3_BUCKET_NAME = 's3_bucket'
AWS_S3_KEY_NAME = 's3_key'
