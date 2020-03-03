#!/usr/bin/env python -i
import logging
import copy

from typing import Union, List

from datetime import datetime

from .constants import (
    GENERIC_ADAPTER,
    PROCESS_TOO_COMPLEX,
    PROCESS_COMPLEX,
    PROCESS_SIMPLE_ARRAY,
    PROCESS_SIMPLE,
    PROCESS_UNKNOWN,
    SIMPLE_TYPES,
)

logger = logging.getLogger(f'axonius.{__name__}')


def listify(obj: Union[str, list, tuple, int, datetime, float, bool]) -> list:
    """Convert obj into a list.

    Args:
        obj: object to force into list format

    Returns:
        list

    """
    if isinstance(obj, tuple):
        return list(obj)

    if obj is None:
        return []

    if not isinstance(obj, list):
        return [obj]

    return obj


def build_selected_map(entity_fields: dict, selected: Union[dict, list, tuple], excluded: List[str] = None) -> dict:
    """Create dict of selected items in entity fields.

    Args:
        entity_fields: the schema of the fields for this asset type
        selected: the fields selected by the user
        excluded: the fields to exclude from parsing

    Returns:
        flattened dict of selected fields with their type handlers mapped

    """
    msg = f'Start build of selected map for selected {selected} and excluded {excluded}'
    logger.debug(msg)

    entity_fields = copy.deepcopy(entity_fields)
    excluded = excluded or []
    selected = {x: None for x in selected if x not in excluded}

    # turn entity fields into a flat dict for easy lookup
    flat_fields = {}
    for field in entity_fields['generic']:
        field['adapter'] = GENERIC_ADAPTER
        flat_fields[field['name']] = field

    for adapter, fields in entity_fields['specific'].items():
        for field in fields:
            field['adapter'] = adapter
            flat_fields[field['name']] = field

    for field_name in list(selected):
        if field_name not in flat_fields:
            msg = f'Unable to find {field_name} in flat fields! This should not happen.'
            logger.error(msg)
            continue

        field = flat_fields[field_name]
        selected[field_name] = handle_field(field=field, parent={})

    msg = f'Finish build of selected map'
    logger.debug(msg)

    return selected


def handle_field(field: dict, parent: dict) -> dict:
    """Add header, headers, and process keys to a field."""
    field['headers'] = field.get('headers', [])

    if parent:  # child field of complex field
        # make this fields header parents header + this fields title
        field['header'] = build_header(parts=[parent['header'], field['title']])

        if is_complex(field):  # complex field under complex field, too complex
            parent['headers'].append(field['header'])
            field['process'] = PROCESS_TOO_COMPLEX
        else:
            parent['headers'].append(field['header'])
            field['process'] = get_simple_process(field)

    else:  # root field
        # make this fields header canon adapter name + this fields title
        # FUTURE: would be better to have proper name of adapter in plugin_meta.js also stored in entity.
        adapter_name = build_canon_name(name=field['adapter'])
        field['header'] = build_header(parts=[adapter_name, field['title']])

        if is_complex(field):  # complex field at root level, can be flattened
            field['process'] = PROCESS_COMPLEX

            items = field['items'].pop('items')
            items = [x for x in items if '.' not in x['name']]  # dont process nested items
            field['items']['items'] = {}
            for item in items:
                item = handle_field(field=item, parent=field)
                field['items']['items'][item['name']] = item

        else:  # simple field at root level
            field['headers'].append(field['header'])
            field['process'] = get_simple_process(field)

    return field


def get_simple_process(field: dict) -> str:
    """Update field with process key."""
    if is_simple_array(field):
        # just an array of simples
        return PROCESS_SIMPLE_ARRAY
    if is_simple(field):
        # just a simple
        return PROCESS_SIMPLE

    msg = f'Unknown field type hit - this should not happen! {field}'
    logger.error(msg)
    return PROCESS_UNKNOWN


def build_canon_name(name: dict) -> str:
    """Build a canonical name of a field or adapter name."""
    return ' '.join(name.replace('_adapter', '').split('_')).title()


def get_items(field: dict) -> dict:
    """Get items in field."""
    return field.get('items', {})


def get_items_type(field: dict) -> str:
    """Get type of items in field."""
    return get_items(field).get('type', '')


def get_type(field: dict) -> str:
    """Get type of field."""
    return field.get('type', '')


def is_complex(field: dict) -> bool:
    """Check if field is a complex field (has sub fields)."""
    return get_items_type(field) == 'array'


def is_array(field: dict) -> bool:
    """Check if field is an array."""
    return get_type(field) == 'array'


def is_simple_array(field: dict) -> bool:
    """Check if field is an array of simples."""
    return is_array(field) and get_items_type(field) in SIMPLE_TYPES


def is_simple(field: dict) -> bool:
    """Check if field is simple."""
    return get_type(field) in SIMPLE_TYPES


def build_header(parts: list) -> str:
    """Build a header by joining parts."""
    return ': '.join([x for x in parts if x])
