import csv
import io
import logging
from datetime import datetime
from uuid import uuid4
from flask import request, session, jsonify

from axonius.plugin_base import EntityType, return_error, PluginBase
from axonius.utils.gui_helpers import (get_historized_filter, parse_entity_fields, merge_entities_fields,
                                       flatten_fields, get_generic_fields, get_csv_canonized_value)
from axonius.utils.axonius_query_language import (convert_db_entity_to_view_entity, convert_db_projection_to_view)
from axonius.consts.plugin_consts import NOTES_DATA_TAG
from axonius.consts.gui_consts import PREDEFINED_ROLE_ADMIN
from axonius.entities import AXONIUS_ENTITY_BY_CLASS, AxoniusEntity

from gui.gui_logic.get_ec_historical_data_for_entity import (TaskData, get_all_task_data)

logger = logging.getLogger(f'axonius.{__name__}')


def _fetch_historical_entity(entity_type: EntityType, entity_id, projection=None, history_date: datetime = None):
    """
    Fetch the single matching Entity, converted to the view structure

    :param entity_type:  Type of entity to search for
    :param entity_id:    internal_axon_id to find the entity by
    :param projection:   The fields to retrieve for the entity
    :param history_date: The date from which to retrieve the data
    :return:
    """
    return convert_db_entity_to_view_entity(PluginBase.Instance.get_appropriate_view(history_date, entity_type).
                                            find_one(get_historized_filter({
                                                'internal_axon_id': entity_id
                                            }, history_date), projection=convert_db_projection_to_view(projection)),
                                            ignore_errors=True)


def get_entity_data(entity_type: EntityType, entity_id, history_date: datetime = None):
    """
    Fetch the general data needed for a single entity, excluding advanced fields which are fetched separately
    (defined by mongo_projection_out)

    :param entity_id:            internal_axon_id to find the entity by
    :param entity_type:          Type of entity to search for
    :param history_date:         The date from which to retrieve the data
    :return:
    """
    entity = _fetch_historical_entity(entity_type, entity_id, history_date=history_date)
    if entity is None:
        return return_error('Entity ID wasn\'t found', 404)

    # Fix notes to have the expected format of user id
    for item in entity['generic_data']:
        if item.get('name') == 'Notes' and item.get('data'):
            item['data'] = [{**note, **{'user_id': str(note['user_id'])}} for note in item['data']]

    def _filter_long_data(data):
        if not isinstance(data, dict):
            return data
        new_data = {}
        for k, v in data.items():
            if isinstance(v, dict):
                new_data[k] = _filter_long_data(v)
            if isinstance(v, list):
                new_data[k] = [_filter_long_data(x) for x in v if not isinstance(x, bytes)]
            elif isinstance(v, str) and len(v) > 128:
                new_data[k] = f'{v[:128]}...'
            elif not isinstance(v, bytes):
                new_data[k] = v
        return new_data

    for specific in entity['specific_data']:
        if not specific.get('data') or not specific['data'].get('raw'):
            continue
        specific['data']['raw'] = _filter_long_data(specific['data']['raw'])

    def _is_table(schema):
        return schema['type'] == 'array' and schema.get('format', '') == 'table'

    # Separate simple fields and those defined to be formatted as a Table
    generic_fields = get_generic_fields(entity_type)
    advanced_data = []
    basic_fields = []
    for schema in generic_fields['items']:
        if _is_table(schema):
            schema_name = f'specific_data.data.{schema["name"]}'
            advanced_field_data = parse_entity_fields(entity, [schema_name]).get(schema_name)
            flat_schema = {**schema, 'items': flatten_fields(schema['items'])}
            if advanced_field_data:
                advanced_data.append({
                    'schema': flat_schema,
                    'data': [parse_entity_fields(row, [field['name'] for field in flat_schema['items']])
                             for row in advanced_field_data]
                })
        else:
            basic_fields.append(schema)

    return {
        'basic': parse_entity_fields(entity, [field['name'] for field in flatten_fields({
            'type': 'array',
            'items': basic_fields
        }, 'specific_data.data')]),
        'advanced': advanced_data,
        'data': entity['generic_data'],
        'adapters': entity['specific_data'],
        'labels': entity['labels'],
        'updated': entity.get('accurate_for_datetime', None)
    }


def entity_data_field_csv(entity_type: EntityType, entity_id, field_name, mongo_sort=None,
                          history_date: datetime = None, field_filters: dict = None):
    """
    Generate a csv file from the data of given field, with fields' pretty titles as coloumn headers

    :param entity_type:  Type of entity to search for
    :param entity_id:    internal_axon_id to find the entity by
    :param field_name:   The main field to get data for
    :param mongo_sort:   The inner field to sort by
    :param history_date: The date from which to retrieve the data
    :return:
    """
    field_name_full = f'specific_data.data.{field_name}'
    entity = _fetch_historical_entity(entity_type, entity_id, {
        field_name_full: 1
    }, history_date)

    string_output = io.StringIO()
    # Make a flat list of all fields under requested tabular field
    fields = next(flatten_fields(field['items']) for field in get_generic_fields(entity_type)['items']
                  if field['name'] == field_name)
    field_by_name = {
        field['name']: field for field in fields
        if not isinstance(field.get('items'), list)
    }
    entity_field_data = merge_entities_fields(
        parse_entity_fields(entity, [field_name_full]).get(field_name_full, []), field_by_name.keys())
    if not len(entity_field_data):
        return string_output

    field_by_name = {
        field: field_by_name[field] for field in field_by_name.keys()
        if any(data.get(field) is not None for data in entity_field_data)
    }
    if mongo_sort:
        sort_field = request.args.get('sort')
        default_value = None
        if field_by_name[sort_field]['type'] == 'string':
            if field_by_name[sort_field].get('format') and 'date' in field_by_name[sort_field]['format']:
                default_value = datetime.min
            else:
                default_value = ''
        elif field_by_name[sort_field]['type'] in ['integer', 'number']:
            default_value = 0
        elif field_by_name[sort_field]['type'] == 'bool':
            default_value = False
        elif field_by_name[sort_field]['type'] == 'array':
            default_value = []
        entity_field_data.sort(key=lambda row: row.get(sort_field, default_value),
                               reverse=request.args.get('desc') == '1')
    for data in entity_field_data:
        for field in field_by_name.keys():
            # Replace field paths with their pretty titles
            if field in data:
                field_filter = field_filters.get(field, '') if field_filters else ''
                data[field_by_name[field]['title']] = get_csv_canonized_value(data[field], field_filter)
                del data[field]

    dw = csv.DictWriter(string_output, [field['title'] for field in field_by_name.values()])
    dw.writeheader()
    dw.writerows(entity_field_data)
    return string_output


def entity_tasks(entity_id):
    """
    Get any task that ran on the id

    """
    return TaskData.schema().dump(list(get_all_task_data(entity_id)), many=True)


##############
# User Notes #
##############


def entity_notes(entity_type: EntityType, entity_id, request_data):
    """
    Method for fetching, creating or deleting the notes for a specific entity, by the id given in the rule

    :param entity_type:  Type of entity in subject
    :param entity_id:    ID of the entity to handle notes of
    :param request_data: Object data from the request
    :return:             GET, list of notes for the entity
    """
    entity_doc = _fetch_historical_entity(entity_type, entity_id)
    if not entity_doc:
        logger.error(f'No entity found with internal_axon_id = {entity_id}')
        return return_error(f'No entity found with internal_axon_id = {entity_id}', 400)

    entity_obj = AXONIUS_ENTITY_BY_CLASS[entity_type](PluginBase.Instance, entity_doc)
    notes_list = entity_obj.get_data_by_name(NOTES_DATA_TAG)
    if notes_list is None:
        notes_list = []

    if request.method == 'PUT':
        return _entity_notes_create(request_data, notes_list, entity_obj)

    # Handle remaining option - DELETE request
    return _entity_notes_delete(request_data, notes_list, entity_obj)


def _entity_notes_create(note_obj, notes_list, entity_obj: AxoniusEntity):
    """
    Add a new note to the DB entity

    :param note_obj:    Note in the structure received from GUI and
    :param notes_list:  Current notes of the entity (could be empty)
    :param entity_obj:  To add note to
    :return:            The note along with id of user that created it
    """
    current_user = session['user']
    note_obj['user_id'] = current_user['_id']
    note_obj['user_name'] = f'{current_user["source"]}/{current_user["user_name"]}'
    note_obj['accurate_for_datetime'] = datetime.now()
    note_obj['uuid'] = str(uuid4())
    notes_list.append(note_obj)
    entity_obj.add_data(NOTES_DATA_TAG, notes_list, action_if_exists='merge')
    note_obj['user_id'] = str(note_obj['user_id'])
    return jsonify(note_obj)


def _entity_notes_delete(note_ids_list, notes_list, entity_obj: AxoniusEntity):
    """
    Remove existing notes from the DB entity

    :param note_ids_list:   List of ids of the notes to remove
    :param notes_list:      Current notes of the entity (expected to contain the given notes)
    :param entity_obj:      To remove note from
    """
    current_user = session['user']
    if not current_user.get('admin') and current_user.get('role_name') != PREDEFINED_ROLE_ADMIN:
        # Validate all notes requested to be removed belong to user
        for note in notes_list:
            if note['uuid'] in note_ids_list and note['user_id'] != current_user['_id']:
                logger.error('Only Administrator can remove another user\'s Note')
                return return_error('Only Administrator can remove another user\'s Note', 400)
    remaining_notes_list = []
    for note in notes_list:
        if note['uuid'] not in note_ids_list:
            remaining_notes_list.append(note)
    entity_obj.add_data(NOTES_DATA_TAG, remaining_notes_list, action_if_exists='merge')
    return ''


def entity_notes_update(entity_type: EntityType, entity_id, note_id, note_obj):
    """
    Update the content of a specific note attached to a specific entity.
    This operation will update accurate_for_datetime.
    If this is called by an Administrator for a note of another user, the user_name will be changed too.

    :param entity_id:   internal_axon_id of entity to edit the note of
    :param note_id:     Specific note of the entity, to edit content of
    :return:
    """
    entity_doc = _fetch_historical_entity(entity_type, entity_id, None)
    if not entity_doc:
        logger.error(f'No entity found with internal_axon_id = {entity_id}')
        return return_error('No entity found for selected ID', 400)

    entity_obj = AXONIUS_ENTITY_BY_CLASS[entity_type](PluginBase.Instance, entity_doc)
    notes_list = entity_obj.get_data_by_name(NOTES_DATA_TAG)
    note_doc = next(x for x in notes_list if x['uuid'] == note_id)
    if not note_doc:
        logger.error(f'Entity with internal_axon_id = {entity_id} has no note at index = {note_id}')
        return return_error('Selected Note cannot be found for the Entity', 400)

    current_user = session['user']
    if current_user['_id'] != note_doc['user_id'] and not current_user.get('admin') and \
            current_user.get('role_name') != PREDEFINED_ROLE_ADMIN:
        return return_error('Only Administrator can edit another user\'s Note', 400)

    note_doc['note'] = note_obj
    note_doc['user_id'] = current_user['_id']
    note_doc['user_name'] = f'{current_user["source"]}/{current_user["user_name"]}'
    note_doc['accurate_for_datetime'] = datetime.now()
    entity_obj.add_data(NOTES_DATA_TAG, notes_list, action_if_exists='merge')
    note_doc['user_id'] = str(note_doc['user_id'])
    return jsonify(note_doc)
