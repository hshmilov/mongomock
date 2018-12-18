PAGE_NUMBER_FLOOD_PROTECTION = 1000


def get_paginated_next_token_api(func):
    next_token = None
    page_number = 0

    while page_number < PAGE_NUMBER_FLOOD_PROTECTION:
        page_number += 1
        if next_token:
            result = func(nextToken=next_token)
        else:
            result = func()

        yield result

        next_token = result.get('nextToken')
        if not next_token:
            break
