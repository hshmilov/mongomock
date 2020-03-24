
RESOURCE_PATH_DESCRIPTION = '''Path can be either an HTTP(S) URL, or an SMB share path.
When specifying a URL, the endpoint must support the HTTP GET method.
All urls must start with HTTP:// or HTTPS:// .
The optional username and password will be used for BASIC authentication, if provided.
When specifying an SMB Share path, the path must start with double-backslashes ("\\\\").
Username and password, if provided for an SMB path, will be used to authentication.'''

AWS_ENDPOINT_FOR_REACHABILITY_TEST = f'https://apigateway.us-east-2.amazonaws.com/'   # endpoint for us-east-2

FILE_CLIENTS_SCHEMA = [
    {
        'name': 'user_id',
        'title': 'File name',
        'type': 'string'
    },
    {
        'name': 'file_path',
        'title': 'Upload file',
        'description': 'Select a file to upload.',
        'type': 'file'
    },
    {
        'name': 'resource_path',
        'title': 'Path to resource (SMB/URL)',
        'description': RESOURCE_PATH_DESCRIPTION,
        'type': 'string'
    },
    {
        'name': 'username',
        'title': 'User name for online resource (Share/URL)',
        'type': 'string'
    },
    {
        'name': 'password',
        'title': 'Password for online resource (Share/URL)',
        'type': 'string',
        'format': 'password',
    },
    {
        'name': 's3_bucket',
        'title': 'Amazon S3 bucket name',
        'type': 'string',
    },
    {
        'name': 's3_object_location',
        'title': 'Amazon S3 object location (key)',
        'type': 'string',
    },
    {
        'name': 's3_use_ec2_attached_instance_profile',
        'title': 'Amazon S3 Use EC2 Attached Instance Profile',
        'type': 'bool'
    },
    {
        'name': 's3_access_key_id',
        'title': 'Amazon S3 Access Key ID',
        'description': 'Leave blank to use the attached IAM role',
        'type': 'string',
    },
    {
        'name': 's3_secret_access_key',
        'title': 'Amazon S3 Secret Access Key',
        'description': 'Leave blank to use the attached IAM role',
        'type': 'string',
        'format': 'password'
    },
    {
        'name': 'encoding',
        'title': 'Encoding',
        'type': 'string'
    },
    {
        'name': 'verify_ssl',
        'title': 'Verify SSL',
        'type': 'bool'
    },
    {
        'name': 'http_proxy',
        'title': 'HTTP proxy',
        'type': 'string'
    },
    {
        'name': 'https_proxy',
        'title': 'HTTPS proxy',
        'type': 'string'
    },
    {
        'name': 'request_headers',
        'title': 'Additional HTTP headers',
        'type': 'string',
        'description': 'JSON-formatted dictionary of custom HTTP headers '
                       'to add to request.',
    },
    {
        'name': 'suppress_netbios',
        'title': 'Suppress NetBIOS name lookup',
        'type': 'bool',
        'default': False,
        'description': 'Select this to suppress NetBios name lookup when using SMB share'
    }
]

FILE_SCHEMA_REQUIRED = [
    'user_id',
    's3_use_ec2_attached_instance_profile'
]
