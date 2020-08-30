SQL_INSTANCE_STATES = [
    'SQL_INSTANCE_STATE_UNSPECIFIED',
    'RUNNABLE',
    'SUSPENDED',
    'PENDING_DELETE',
    'PENDING_CREATE',
    'MAINTENANCE',
    'FAILED',
]
SQL_DB_VERSIONS = [
    'SQL_DATABASE_VERSION_UNSPECIFIED',
    'MYSQL_5_5',
    'MYSQL_5_6',
    'MYSQL_5_7',
    'POSTGRES_9_6',
    'POSTGRES_10',
    'POSTGRES_11',
    'POSTGRES_12',
    'SQLSERVER_2017_STANDARD',
    'SQLSERVER_2017_ENTERPRISE',
    'SQLSERVER_2017_EXPRESS',
    'SQLSERVER_2017_WEB',
]
SQL_SUSP_REASONS = [
    'SQL_SUSPENSION_REASON_UNSPECIFIED',
    'BILLING_ISSUE',
    'LEGAL_ISSUE',
    'OPERATIONAL_ISSUE',
    'KMS_KEY_ISSUE',
]
SQL_INSTANCE_TYPES = [
    'CLOUD_SQL_INSTANCE',
    'ON_PREMISES_INSTANCE',
    'READ_REPLICA_INSTANCE',
    'SQL_INSTANCE_TYPE_UNSPECIFIED'
]

SCC_FINDING_STATES = [
    'STATE_UNSPECIFIED',
    'ACTIVE',
    'INACTIVE',
]

# XXX Add more resources here when new device types are added to the adapter
DEFAULT_SCC_WHITELIST = [
    'compute.Instance',  # vm
    'storage.Bucket',  # storage device
    'sqladmin.Instance',  # sql db
]

SCC_BAD_RESOURCE = 'compute.InstanceGroup'  # XXX Convert this to a list if absolutely necessary (keep url short)

SCC_DAYS_MAX = 90
