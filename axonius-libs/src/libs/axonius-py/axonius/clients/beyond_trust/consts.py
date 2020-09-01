USER = 'username'
PASSWORD = 'password'
BEYOND_TRUST_HOST = 'server'
BEYOND_TRUST_PORT = 'port'
DEFAULT_BEYOND_TRUST_DATABASE = 'BeyondTrustReporting'
DEFAULT_BEYOND_TRUST_PORT = 1433
BEYOND_TRUST_DATABASE = 'database'
DRIVER = 'driver'
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'
DEFAULT_RECORDS_PER_QUERY = 1000

# I'm using select * intentionally as we need all the fields (Reasonable amount)
DOMAINS_QUERY = 'select * , Domains.Name as DomainName from Domains'
POLICIES_QUERY = 'select * , Policies.ID as PolicyID , Policies.Name as PolicyName from Policies'
DEVICES_QUERY = 'select * , Hosts.Name as HostName from Hosts'
USERS_QUERY = 'select * , Users.Name as UserName from Users'

# Get all user sessions with the most recent LogonTime, Maximum rows in th result will be Count(Users)
# pylint: disable=C4002
USER_SESSIONS_QUERY = """
    select
      *
    from (select
      *,
      ROW_NUMBER() OVER (
      PARTITION by UserID
      order by LogonTime DESC) as RowNumber
    from UserSessions) as FilteredRows
    where RowNumber = 1
"""
