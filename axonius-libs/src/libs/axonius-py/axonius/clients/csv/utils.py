import logging
import datetime
from collections import OrderedDict

from typing import Dict, List

from axonius.utils.datetime import parse_date

logger = logging.getLogger(f'axonius.{__name__}')


# pylint: disable=too-many-branches, too-many-statements
def get_column_types(csv_data: List[OrderedDict]) -> Dict[str, type]:
    column_types = dict()
    for line in csv_data:
        for column_name, column_value in line.items():
            if not column_name or not column_value:
                continue

            if column_name not in column_types:
                # Make a first guess.
                # since a regular number ('8') can be treated as an int/float and as a date
                # we prefer an int/float first (leaving only space for string-dates for datetime)

                try:
                    int(column_value)
                    column_types[column_name] = int
                    continue
                except ValueError:
                    pass

                try:
                    float(column_value)
                    column_types[column_name] = float
                    continue
                except ValueError:
                    pass

                if parse_date(column_value):
                    column_types[column_name] = datetime.datetime
                    continue

                column_types[column_name] = str
                continue

            # If its a datetime or an int/float, keep checking this continues. Otherwise convert to str.
            current_assumed_type = column_types[column_name]
            if isinstance(current_assumed_type, str):
                continue

            if current_assumed_type == datetime.datetime:
                if not parse_date(column_value):
                    column_types[column_name] = str
                    continue
                # If we think its a datetime but its also can be parsed as int/float, then treat it as mixed
                # (the value "9" can be a date..)
                try:
                    float(column_value)
                    column_types[column_name] = str
                except ValueError:
                    pass
                continue

            if current_assumed_type == float:
                try:
                    float(column_value)
                except ValueError:
                    column_types[column_name] = str
                continue

            if current_assumed_type == int:
                try:
                    int(column_value)
                except ValueError:
                    # If its not int it might be float.
                    try:
                        float(column_value)
                        column_types[column_name] = float
                    except ValueError:
                        column_types[column_name] = str
                continue

    return column_types
