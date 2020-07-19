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

from .tools import listify, build_selected_map

logger = logging.getLogger(f'axonius.{__name__}')


def handle_entities(stream: io.StringIO, entity_fields: dict, selected: Union[dict, List[str]], entities: List[dict],
                    excluded: List[str] = None, cell_joiner: str = None, max_rows: int = None) -> Iterable[str]:
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

        row = process_entity(entity, selected_map, cell_joiner)
        if row:
            yield writer.writerow(row)
        # yield writer.writerow(process_entity(entity, selected_map, cell_joiner))


def process_entity(entity: dict, selected_map: dict, cell_joiner: str) -> dict:
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
        if not field.get('header') or not field.get('process'):
            continue
        header = field['header']
        processor = field['process']

        value = entity.pop(field_name)

        if processor == PROCESS_COMPLEX:
            entity.update(process_complex(value=value, field=field, cell_joiner=cell_joiner))
        elif processor == PROCESS_TOO_COMPLEX:
            entity[header] = TOO_COMPLEX_STR
        else:
            entity[header] = process_simple(value=value, field=field, cell_joiner=cell_joiner)
    return entity


def process_complex(value: list, field: dict, cell_joiner: str) -> dict:
    """Process a complex field.

    - Will remove the complex field raw name
    - Will add new fields for each sub field, with values index correlated to other sub fields
    """
    values = {}

    item_fields = field['items']['items']

    for item in value:
        for item_name in list(item):
            if item_name not in item_fields:
                # this happens with items ending with _raw, don't care about those
                continue

            item_field = item_fields[item_name]
            header = item_field['header']

            values[header] = values.get(header, [])
            values[header] += listify(item.pop(item_name))

    for k, v in values.items():
        values[k] = process_simple(value=v, field=field, cell_joiner=cell_joiner)
    return values


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
