from typing import List

from axonius.consts.report_consts import ACTIONS_MAIN_FIELD, ACTIONS_FAILURE_FIELD, ACTIONS_POST_FIELD, \
    ACTIONS_SUCCESS_FIELD


def extract_actions_from_ec(actions: dict) -> List[dict]:
    """
    Example input:
    "actions": {
        "failure": [A,B],
        "main": C,
        "post": [],
        "success": [D]
    }
    Example output:
    [C, A, B, D]
    (Order is not guaranteed)
    """
    return [actions[ACTIONS_MAIN_FIELD]] + actions[ACTIONS_SUCCESS_FIELD] + \
        actions[ACTIONS_FAILURE_FIELD] + actions[ACTIONS_POST_FIELD]
