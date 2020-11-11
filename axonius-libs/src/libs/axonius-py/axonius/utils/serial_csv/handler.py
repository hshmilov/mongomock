#!/usr/bin/env python -i
import io
import codecs
import csv
import logging
from typing import Union, List, Iterable

from datetime import datetime

from .constants import (
    PROCESS_COMPLEX,
    PROCESS_TOO_COMPLEX,
    TOO_COMPLEX_STR,
    DTFMT,
    CELL_MAX_LEN,
    CELL_MAX_STR,
    CELL_JOIN_DEFAULT,
    MAX_ROWS_LEN,
    MAX_ROWS_STR,
)

from .tools import build_selected_map

logger = logging.getLogger(f'axonius.{__name__}')
COMPLEX = 'complex_'


def handle_entities(stream: io.StringIO, entity_fields: dict, selected: Union[dict, List[str]], entities: List[dict],
                    excluded: List[str] = None, cell_joiner: str = None, max_rows: int = None,
                    null_value: str = '') -> Iterable[str]:
    """Return an iterator of csv lines.

    - Will get predicted headers from selected_map from build_selected_map.
    - Will determine cell_joiner based on OS if none supplied.
    - Will trim entities if over MAX_ROWS_LEN.
    """
    logger.info(f'Start CSV export handler')
    logger.debug(f'CSV handler selected: {selected}')
    logger.debug(f'CSV handler excluded: {excluded}')
    logger.debug(f'CSV handler stream: {stream}')
    logger.debug(f'CSV handler cell_joiner: {cell_joiner}')

    selected_map = build_selected_map(entity_fields=entity_fields, selected=selected, excluded=excluded)

    headers = []
    for i in selected_map.values():
        if i:
            headers += i['headers']

    if not cell_joiner:
        cell_joiner = CELL_JOIN_DEFAULT

    if not max_rows:
        max_rows = MAX_ROWS_LEN

    bom = codecs.BOM_UTF8.decode('utf-8')
    stream.write(bom)
    yield bom

    writer = csv.DictWriter(f=stream, fieldnames=headers, quoting=csv.QUOTE_NONNUMERIC)

    yield writer.writerow(dict(zip(headers, headers)))

    entity_cnt = 0
    for entity in entities:
        entity_cnt += 1
        if entity_cnt > max_rows:
            msg = f'{entity_cnt} entities is more than {max_rows}, trimming'
            logger.warning(msg)
            yield writer.writerow({headers[0]: MAX_ROWS_STR.format(MAX_ROWS_LEN=max_rows)})
            break

        row = process_entity(entity=entity, selected_map=selected_map, cell_joiner=cell_joiner, null_value=null_value)
        if row:
            copy_row = row.copy()
            row_list = [copy_row[field] for field in copy_row.keys() if field.replace(COMPLEX, '') in headers]
            yield writer.writer.writerow(row_list)


def process_entity(entity: dict, selected_map: dict, cell_joiner: str, null_value: str = '') -> dict:
    """Process an entity.

    - Changes the key of a field to the header defined in selected_map.
    - Processes complex or simple fields based on processor defined in selected_map.
    """
    for field_name in list(entity):
        if field_name not in selected_map:
            msg = f'Field {field_name} not in {list(selected_map)}'
            logger.error(msg)
            continue

        field = selected_map[field_name]
        if not field or not field.get('header') or not field.get('process'):
            continue
        header = field['header']
        processor = field['process']

        value = entity.pop(field_name)

        if processor == PROCESS_COMPLEX:
            result = process_complex(value=value, field=field, cell_joiner=cell_joiner, null_value=null_value)
            entity.update({f'{COMPLEX}{field}': result[field] for field in result})
        elif processor == PROCESS_TOO_COMPLEX:
            entity[header] = TOO_COMPLEX_STR
        else:
            entity[header] = process_simple(value=value, field=field, cell_joiner=cell_joiner)
    return entity


def process_complex(value: list, field: dict, cell_joiner: str, null_value: str = '') -> dict:
    """Process a complex field.

    - Will remove the complex field raw name
    - Will add new fields for each sub field, with values index correlated to other sub fields
    """
    new_value = {}

    # get the schemas of the sub-fields for this complex field
    schemas = field['items']['items']  # item_fields

    for schema_name, schema in schemas.items():
        # get the header to use for this sub-field
        header = schema['header']

        # add the header as a key to new_value
        new_value[header] = []

        # for each row in the complex field
        for item in value:
            # get the value for this sub-field from the current row, defaulting to null_value
            item_value = item.pop(schema_name, null_value)
            # coerce the value into a list
            item_value = item_value if isinstance(item_value, (tuple, list)) else [item_value]
            # add the value to the key for this schemas header in new values
            new_value[header] += item_value

    # join the list values using the same logic as simple fields use
    new_value = {k: process_simple(value=v, field=field, cell_joiner=cell_joiner) for k, v in new_value.items()}
    return new_value


def process_simple(value: Union[str, int, float, datetime, list, tuple], field: dict, cell_joiner: str) -> str:
    """Process a simple field.

    - Turns a list into a str joined using cell_joiner.
    - Converts datetime objects to str.
    - Cuts cells to CELL_MAX_LEN if over.
    """
    if isinstance(value, (tuple, list)):
        value = [process_simple(value=x, field=field, cell_joiner=cell_joiner) for x in value]
        value = cell_joiner.join(value)

    if isinstance(value, datetime):
        value = value.strftime(DTFMT)

    if len(format(value)) >= CELL_MAX_LEN:
        value = cell_joiner.join([format(value)[:CELL_MAX_LEN], CELL_MAX_STR])

    return format(value)
