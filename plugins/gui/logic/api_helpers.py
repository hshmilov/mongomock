import logging
import math

logger = logging.getLogger(f'axonius.{__name__}')


def get_page_metadata(skip, limit, number_of_assets, number=0):
    return {
        'number': math.floor((skip / limit) + 1) if limit != 0 and number == 0 else number,  # Current page number
        'size': min(max(number_of_assets - skip, 0), limit),  # Number of assets in current page
        'totalPages': math.ceil(number_of_assets / limit) if limit != 0 else 0,  # Total number of pages
        'totalResources': number_of_assets  # Total number of assets filtered
    }
