DEFAULT_MYSQL_SPECIAL_PORT = 3306
DRIVER = 'driver'
DEVICES_FETECHED_AT_A_TIME = 'devices_fetched_at_a_time'

HOST_TABLE = 'host'
CRAWLER_TABLE = 'crawler'
VMHOST_TABLE = 'vmhostintersect'

MYSQL_SPECIAL_HOST_QUERY = f'Select * from {HOST_TABLE}'
MYSQL_SPECIAL_CRAWLER_QUERY = f'Select * from {CRAWLER_TABLE}'
MYSQL_SPECIAL_VMHOST_QUERY = f'Select * from {VMHOST_TABLE}'

MYSQL_SPECIAL_WHERE_CLAUSE = ' where scrapedate >= (DATE(NOW()) - INTERVAL {days_ago} DAY) ORDER BY scrapedate DESC'
