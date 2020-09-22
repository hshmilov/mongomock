from typing import List, Pattern

MAX_ITERATIONS: int = 10
DEFAULT_API_PORT: int = 8443
BASE_ENDPOINT: str = 'api/v2'
IPV4_REGEX: Pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
SECONDS_IN_A_DAY: int = 86400
ASYNC_DEVICE_LIMIT = 500
ASYNC_DEVICE_TRIGGER: int = 501
ASYNC_JOB_STATUS_FAILED = 'failed'
ASYNC_JOB_STATUS_DONE = 'done'
ASYNC_JOB_STATUS_FINISHED: List[str] = [ASYNC_JOB_STATUS_DONE, ASYNC_JOB_STATUS_FAILED]
ASYNC_DEFAULT_RETRY_AFTER: int = 5
ASYNC_EXTRA_HEADERS: dict = {'Prefer': 'respond-async'}
RULESET_STATUS: str = 'active'
DEVICE_ENDPOINT: str = 'orgs/{org_id}/vens'
RULESET_ENDPOINT: str = 'orgs/{org_id}/sec_policy/{status}/rule_sets'
SUCCESS_CODES: List[int] = [200, 201, 204]
DEVICE_TYPE = {'ven': 'VENs', 'rule': 'rulesets'}
