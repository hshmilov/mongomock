import csv
import io
import json
import logging
from datetime import datetime
from typing import Generator, List
from uuid import uuid4

from pymongo import DESCENDING
from flask import request, session, jsonify

from axonius.consts.gui_consts import CORRELATION_REASONS, HAS_NOTES, HAS_NOTES_TITLE
from axonius.consts.plugin_consts import NOTES_DATA_TAG, PLUGIN_UNIQUE_NAME
from axonius.entities import AXONIUS_ENTITY_BY_CLASS, AxoniusEntity
from axonius.plugin_base import EntityType, return_error, PluginBase
from axonius.utils.axonius_query_language import (convert_db_entity_to_view_entity, convert_db_projection_to_view)
from axonius.utils.gui_helpers import (get_historized_filter, parse_entity_fields, merge_entities_fields,
                                       flatten_fields, get_generic_fields, get_csv_canonized_value)
from axonius.utils.permissions_helper import is_role_admin
from gui.logic.get_ec_historical_data_for_entity import (TaskData, get_all_task_data)

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
    query_filter = None
    entity = None
    try:
        query_filter = {'internal_axon_id': entity_id}

        entity_col, is_date_filter_required = PluginBase.Instance.get_appropriate_view(history_date, entity_type)
        if is_date_filter_required:
            query_filter = get_historized_filter(query_filter, history_date)
        entity = entity_col.find_one(query_filter, projection=convert_db_projection_to_view(projection))

        return convert_db_entity_to_view_entity(entity, ignore_errors=True)
    except Exception:
        logger.exception(f'Error on {entity_type} on {entity_id}, projection {projection}, history '
                         f'{history_date}, with filter {query_filter} and entity {entity}')
        raise


# pylint: disable=W0212
def fetch_raw_data(entity_type: EntityType, plugin_unique_name: str, id_: str, history_date: datetime = None) -> dict:
    """
    Returns the raw data of the entity
    :param entity_type: Entity type
    :param plugin_unique_name: plugin unique name of the entity adapter
    :param id_: the data.id of the entity
    :param history_date: whether or not to check historical dates
    :return: the raw data or None
    """
    # pylint: disable=W0212
    if history_date:
        col = PluginBase.Instance._raw_adapter_historical_entity_db_map[entity_type]
    else:
        col = PluginBase.Instance._raw_adapter_entity_db_map[entity_type]
    query = {
        PLUGIN_UNIQUE_NAME: plugin_unique_name,
        'id': id_
    }
    if history_date:
        query['accurate_for_datetime'] = history_date
    res = col.find_one(query)
    if not res:
        logger.error(f'Raw data is not present for {plugin_unique_name}, {id_}')
        return None
    return res.get('raw_data')


def _get_entity_actual_data(advance_data: list, items: list) -> Generator[dict, None, None]:
    """
    parse advanced fields data
    @param advance_data: original advanced field data
    @param items: flatted fields schema
    @return: generator with all the parsed data ( can be empty generator if no advanced data found )
    """
    for row in advance_data:
        item = parse_entity_fields(row, [field['name'] for field in items])
        for field_name, field_data in item.items():
            if isinstance(field_data, list):
                try:
                    item[field_name] = list(set(field_data))
                except TypeError:
                    # data type probably not hashable
                    continue
        if item:
            yield item


def get_entity_data(entity_type: EntityType, entity_id, history_date: datetime = None):
    """
    Fetch the Aggregated/general data needed for a single entity, excluding advanced fields which are fetched separately
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

    for specific in entity['specific_data']:
        fix_raw_data(specific, entity_type, history_date)

    def _is_table(schema):
        return schema['type'] == 'array' and schema.get('format', '') == 'table'

    # Separate simple fields and those defined to be formatted as a Table
    generic_fields = get_generic_fields(entity_type)
    custom_fields = [
        {
            'name': 'hostname_preferred',
            'title': 'Preferred Host Name',
            'type': 'string'
        },
        {
            'name': 'os.type_preferred',
            'title': 'Preferred OS Type',
            'type': 'string'
        },
        {
            'name': 'os.distribution_preferred',
            'title': 'Preferred OS Distribution',
            'type': 'string'
        },
        {
            'name': 'os.os_str_preferred',
            'title': 'Preferred Full OS String',
            'type': 'string'
        },
        {
            'name': 'os.bitness_preferred',
            'title': 'Preferred OS Bitness',
            'type': 'string'
        },
        {
            'name': 'os.kernel_version_preferred',
            'title': 'Preferred OS Kernel Version',
            'type': 'string'
        },
        {
            'name': 'os.build_preferred',
            'title': 'Preferred OS Build',
            'type': 'string'
        },
        {
            'name': 'network_interfaces.mac_preferred',
            'title': 'Preferred MAC Address',
            'type': 'string'
        },
        {
            'name': 'network_interfaces.ips_preferred',
            'title': 'Preferred IPs',
            'type': 'string'
        },
        {
            'name': 'device_model_preferred',
            'title': 'Preferred Device Model',
            'type': 'string'
        },
        {
            'name': 'domain_preferred',
            'title': 'Preferred Domain',
            'type': 'string'
        },
        {
            'name': CORRELATION_REASONS,
            'title': 'Correlation Reasons',
            'type': 'string'
        },
        {
            'name': HAS_NOTES,
            'title': HAS_NOTES_TITLE,
            'type': 'bool'
        }
    ]

    # pylint: disable=W0106
    [generic_fields['items'].append(x) for x in custom_fields if x not in generic_fields['items']]
    advanced_data = []
    basic_fields = []
    for schema in generic_fields['items']:
        if _is_table(schema):
            schema_name = f'specific_data.data.{schema["name"]}'
            advanced_field_data = parse_entity_fields(entity, [schema_name]).get(schema_name)
            flat_schema = {**schema, 'items': flatten_fields(schema['items'])}
            if advanced_field_data:
                data = list(_get_entity_actual_data(advanced_field_data, flat_schema['items']))
                if data:
                    advanced_data.append({
                        'schema': flat_schema,
                        'data': data
                    })
        else:
            basic_fields.append(schema)

    flattened_basic_fields = [field['name'] for field in flatten_fields({
        'type': 'array',
        'items': basic_fields
    }, 'specific_data.data', [HAS_NOTES])]

    # Base level fields doesn't need the "specific_data" prefix, so they should be appended separately
    flattened_basic_fields.append(HAS_NOTES)

    return {
        'basic': parse_entity_fields(entity, flattened_basic_fields),
        'advanced': advanced_data,
        'data': entity['generic_data'],
        'adapters': entity['specific_data'],
        'labels': entity['labels'],
        'updated': entity.get('accurate_for_datetime', None)
    }


def _filter_long_data(data):
    """
    Used by fix_raw_data
    Used to remove long old data
    """
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


def fix_raw_data(specific: dict, entity_type: EntityType, history_date: datetime):
    """
    Fixes raw for specific_data
    :param specific: the specific data to fix for
    :param entity_type: The entity type used
    :param history_date: the date to fix for
    :return:
    """
    specific_data = specific.get('data')
    if specific_data:
        specific_raw = specific['data'].get('raw')
        if specific_raw:
            specific['data']['raw'] = _filter_long_data(specific_raw)
        else:
            id_ = specific_data.get('id')
            if id_:
                raw_data = fetch_raw_data(entity_type,
                                          specific[PLUGIN_UNIQUE_NAME],
                                          id_,
                                          history_date=history_date)
                if raw_data:
                    specific['data']['raw'] = _filter_long_data(raw_data)


def entity_data_field_csv(entity_type: EntityType, entity_id, field_name, mongo_sort=None,
                          history_date: datetime = None, field_filters: dict = None, excluded_adapters: dict = None,
                          search_term: str = None):
    """
    Generate a csv file from the data of given field, with fields' pretty titles as coloumn headers

    :param entity_type:  Type of entity to search for
    :param entity_id:    internal_axon_id to find the entity by
    :param field_name:   The main field to get data for
    :param mongo_sort:   The inner field to sort by
    :param search_term:  The search term to filter by
    :param history_date: The date from which to retrieve the data
    :return:
    """
    field_name_full = f'specific_data.data.{field_name}'
    entity = _fetch_historical_entity(entity_type, entity_id, {
        field_name_full: 1
    }, history_date)

    # Make a flat list of all fields under requested tabular field
    fields = next(flatten_fields(field['items']) for field in get_generic_fields(entity_type)['items']
                  if field['name'] == field_name)
    field_by_name = {
        field['name']: field for field in fields
        if field.get('type') != 'array' or field.get('items').get('type') != 'array'
    }
    entity_field_data = merge_entities_fields(
        parse_entity_fields(entity, [field_name_full], field_filters=field_filters,
                            excluded_adapters=excluded_adapters).get(field_name_full, []), field_by_name.keys())

    if search_term:
        def search_term_in_row_value(field_value):
            return (search_term in field_value or
                    isinstance(field_value, list) and any(search_term in str(s) for s in field_value))

        def filter_entity_row(entity_field):
            return any(search_term_in_row_value(field_value) for field_value in entity_field.values())

        entity_field_data = list(filter(filter_entity_row, entity_field_data))

    return get_export_csv(entity_field_data, field_by_name, mongo_sort)


def entity_tasks(entity_id: str):
    """
    Get any task that ran on the id

    """
    return TaskData.schema().dump(list(get_all_task_data(entity_id)), many=True)


def entity_tasks_actions(entity_id: str):
    """
    Get any task actions that ran on the id

    """
    tasks = entity_tasks(entity_id)
    actions = []
    for task in tasks:
        for action in task.get('actions'):
            action['additional_info'] = json.dumps(action.get('additional_info', ''))
            actions.append({
                'action_id': f'{task.get("uuid")} {action.get("action_name")}',
                'uuid': task.get('uuid'),
                'recipe_name': get_task_full_name(task.get('recipe_name'), task.get('recipe_pretty_id')),
                **action
            })
    return actions


def entity_tasks_actions_csv(entity_id: str, fields: list, mongo_sort: dict):
    actions = entity_tasks_actions(entity_id)

    field_by_name = {
        field['name']: field for field in fields
        if not isinstance(field.get('items'), list)
    }

    actions_data = []
    for row in actions:
        new_action = {}
        for field in field_by_name.keys():
            new_action[field] = row[field]
        actions_data.append(new_action)

    return get_export_csv(actions_data, field_by_name, mongo_sort)


def sort_data(data: list, field_by_name: dict, sort: dict):
    """
    sort the data by the sort parameter
    :param data: array made of dictionaries
    :param field_by_name: a dictionary of fields
    :param sort: an object containing the field and desc of the sort
    :return: the data sorted
    """
    if sort:
        sort_field, sort_desc = sort.popitem()
        default_value = None
        if field_by_name.get(sort_field):
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

            def sort_key(row):
                sort_value = row.get(sort_field, default_value)
                if sort_value and isinstance(sort_value, list):
                    return ''.join(sort_value)
                return sort_value

            data.sort(key=sort_key, reverse=(int(sort_desc) == DESCENDING))


def get_export_csv(rows: list, field_by_name: dict, sort: dict):
    """
    Export a csv of the rows by the sort
    :param rows: array made of dictionaries
    :param field_by_name: a dictionary of fields
    :param sort: an object containing the field and desc of the sort
    :return: a StringIO containing the csv
    """
    string_output = io.StringIO()
    if not len(rows):
        return string_output
    field_by_name = {
        field: field_by_name[field] for field in field_by_name.keys()
        if any(data.get(field) is not None for data in rows)
    }
    sort_data(rows, field_by_name, sort)
    result_data = []
    for data in rows:
        result_row = {}
        for field in field_by_name.keys():
            # Replace field paths with their pretty titles
            if field in data:
                title = field_by_name[field]['title'] if field_by_name[field]['title'] else field.capitalize()
                result_row[title] = get_csv_canonized_value(data[field])
        result_data.append(result_row)
    dw = csv.DictWriter(string_output, [field['title'] or field['name'].capitalize()
                                        for field in field_by_name.values()])
    dw.writeheader()
    dw.writerows(result_data)
    return string_output


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
        return _entity_notes_create(request_data, notes_list, entity_obj, entity_type, entity_id)

    # Handle remaining option - DELETE request
    return _entity_notes_delete(request_data, notes_list, entity_obj, entity_type, entity_id)


def _entity_notes_create(note_obj, notes_list, entity_obj: AxoniusEntity, entity_type, entity_id):
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

    # Set indicator that there are notes
    PluginBase.Instance.get_appropriate_view(None, entity_type)[0].update_one(
        {
            'internal_axon_id': entity_id
        }, {
            '$set': {HAS_NOTES: True}
        })

    return jsonify(note_obj)


def _entity_notes_delete(note_ids_list, notes_list, entity_obj: AxoniusEntity, entity_type, entity_id):
    """
    Remove existing notes from the DB entity

    :param note_ids_list:   List of ids of the notes to remove
    :param notes_list:      Current notes of the entity (expected to contain the given notes)
    :param entity_obj:      To remove note from
    """
    current_user = session['user']
    if not is_role_admin(current_user):
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

    # Set indicator if there are no notes
    if not remaining_notes_list:
        PluginBase.Instance.get_appropriate_view(None, entity_type)[0].update_one(
            {
                'internal_axon_id': entity_id
            }, {
                '$set': {HAS_NOTES: False}
            })

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
    if current_user['_id'] != note_doc['user_id'] and not is_role_admin(current_user):
        return return_error('Only Administrator can edit another user\'s Note', 400)

    note_doc['note'] = note_obj
    note_doc['user_id'] = current_user['_id']
    note_doc['user_name'] = f'{current_user["source"]}/{current_user["user_name"]}'
    note_doc['accurate_for_datetime'] = datetime.now()
    entity_obj.add_data(NOTES_DATA_TAG, notes_list, action_if_exists='merge')
    note_doc['user_id'] = str(note_doc['user_id'])
    return jsonify(note_doc)


def get_task_full_name(name, pretty_id):
    return f'{name} - Task {pretty_id}'


def get_cloud_admin_users(cloud_name: str, account_id: str) -> List[str]:
    """
        Fetch all cloud (currently aws) admin users.
        Get all users with  AdministratorAccess role. and then, get the users email
        address which can be retrieved from other adapters (the email is fetched not only by aws adapter).

        :param cloud_name:  The cis name, like aws or azure,
        :param account_id: The account id
        :return: the admin user emails list.
        """
    try:
        mail_addresses = []
        users_db = PluginBase.Instance._entity_db_map[EntityType.Users]

        if cloud_name == 'aws':
            all_administrator_access_users = users_db.find(
                {
                    'adapters': {
                        '$elemMatch': {
                            'plugin_name': 'aws_adapter',
                            'data.aws_account_id': str(account_id),
                            'data.has_administrator_access': True
                        }
                    }
                },
                projection={
                    'adapters.data.mail'
                }
            )

            for user in all_administrator_access_users:
                for adapter in (user.get('adapters') or []):
                    if (adapter.get('data') or {}).get('mail'):
                        mail_addresses.append((adapter.get('data') or {}).get('mail'))

        elif cloud_name == 'azure':
            # not implemented yet
            pass

        return mail_addresses
    except Exception:
        logger.info(f'Unable to fetch admin users', exc_info=True)
        return []
