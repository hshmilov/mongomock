import logging
import uuid
import math

from collections import defaultdict
from datetime import datetime
from typing import Iterable, Dict, Iterator, Tuple
from bson import ObjectId

from dataclasses import dataclass
from cachetools import LRUCache
from funcy import chunks
import pymongo
from pymongo.errors import PyMongoError

from axonius.consts.gui_consts import MAX_SORTED_FIELDS, MIN_SORTED_FIELDS
from axonius.utils.get_plugin_base_instance import plugin_base_instance
from axonius.consts.plugin_consts import ADAPTERS_LIST_LENGTH
from axonius.utils.axonius_query_language import convert_db_entity_to_view_entity, parse_filter, \
    convert_db_projection_to_view
from axonius.utils.gui_helpers import parse_entity_fields, get_historized_filter, \
    FIELDS_TO_PROJECT, FIELDS_TO_PROJECT_FOR_GUI, get_sort, nongui_beautify_db_entry, get_entities_count
from axonius.entities import EntityType

logger = logging.getLogger(f'axonius.{__name__}')

ITERATE_CHUNK_SIZE = 50
MAX_CURSORS = 100
# pylint: disable=C0103
cursors = LRUCache(maxsize=MAX_CURSORS)


@dataclass
class CursorMeta:
    data_list: Iterable[dict]
    cursor_id: str
    page_number: int
    asset_count: int


def _normalize_db_projection_for_aggregation(projection: Dict[str, int]):
    """
    If you specify a projection as follows to $project in an aggregation stage:
    {
        'tags.data': 1,
        'tags.data.something': 1
    }
    Mongo yells:
    "Invalid $project :: caused by :: specification contains two conflicting paths."

    Poor mongo, can't handle some real world queries...
    Solution: Eliminate the specific-most projection, and keep the outermost projection.
    """
    indexed = defaultdict(list)
    for k in projection.keys():
        splitted = k.split('.')
        splitted_len = len(splitted)
        if splitted_len > 1:
            indexed[splitted_len].append(splitted)

    for k, v in indexed.items():
        for entry in v:
            for i in range(1, k):
                if '.'.join(entry[:i]) in projection:
                    del projection['.'.join(entry)]
                    break


def _perform_aggregation(entity_views_db,
                         limit, skip, view_filter, sort,
                         projection, entity_type,
                         default_sort) -> Iterator[dict]:
    """
    Performs the required query on the DB using the aggregation method.
    This method is more reliable as it allows for the DB to use the disk by it is much slower in most cases.
    This should be used in cases where the regular (_perform_find) method failed.
    For parameter info see get_entities
    :return:
    """
    pipeline = [{'$match': view_filter}]
    if projection:
        pipeline.append({'$project': projection})
    if sort:
        pipeline.append({'$sort': sort})
    elif entity_type == EntityType.Devices:
        if default_sort:
            # Default sort by adapters list size and then Mongo id (giving order of insertion)
            pipeline.append({'$sort': {ADAPTERS_LIST_LENGTH: pymongo.DESCENDING, '_id': pymongo.DESCENDING}})

    if skip:
        pipeline.append({'$skip': skip})
    if limit:
        pipeline.append({'$limit': limit})

    # Fetch from Mongo is done with aggregate, for the purpose of setting 'allowDiskUse'.
    # This allows bypassing a memory overflow occurring in Mongo
    # https://stackoverflow.com/questions/27023622/overflow-sort-stage-buffered-data-usage-exceeds-internal-limit
    # This should be used as a last resort when all other methods have failed
    return entity_views_db.aggregate(pipeline, allowDiskUse=True)


def _perform_find(entity_views_db,
                  limit, skip, view_filter, sort,
                  projection, entity_type,
                  default_sort) -> Iterator[dict]:
    """
    Tries to perform the given query using the 'find' method on mongo
    For parameter info see get_entities
    :raises PyMongoError: if some mongo error happened
    :return:
    """
    find_sort = list(sort.items())
    if not find_sort and entity_type in (EntityType.Devices, EntityType.Users):
        if default_sort:
            # Default sort by adapters list size and then Mongo id (giving order of insertion)
            find_sort.append((ADAPTERS_LIST_LENGTH, pymongo.DESCENDING))
    return entity_views_db.find(filter=view_filter,
                                sort=find_sort,
                                projection=projection,
                                limit=limit,
                                skip=skip)


def _get_all_entities_raw(skip: int,
                          limit: int,
                          entity_type: EntityType,
                          view_filter: dict,
                          db_projection: dict = None,
                          cursor_id: str = None,
                          sort: dict = None,
                          default_sort: bool = False,
                          history_date: datetime = None
                          ) -> CursorMeta:
    """
    See get_entities for explanation of the parameters
    """
    # pylint: disable=W0603
    global cursors
    cursor_obj = None

    # if the cursor exists, we just want to fetch the next results.
    if cursor_id:
        cursor_obj = cursors.get(cursor_id, None)
        if not cursor_obj:
            raise ValueError(f'Cursor {cursor_id!r} not found')

        cursor_obj.page_number += 1
        return cursor_obj

    if db_projection:
        db_projection, sort = get_db_projection(db_projection=db_projection, sort=sort)

    collection, is_date_filter_required = plugin_base_instance().get_appropriate_view(
        historical=history_date, entity_type=entity_type
    )

    # if we defaulted to normal history collection, add historized_filter
    if history_date and is_date_filter_required:
        view_filter = get_historized_filter(entities_filter=view_filter, history_date=history_date)

    asset_count = get_entities_count(
        entities_filter=view_filter,
        entity_collection=collection,
        history_date=history_date,
        is_date_filter_required=is_date_filter_required,
        quick=False,
    )

    try:
        data_list = _perform_find(
            limit=0,
            skip=skip,
            entity_type=entity_type,
            entity_views_db=collection,
            view_filter=view_filter,
            projection=db_projection,
            sort=sort,
            default_sort=default_sort,
        )
        cursor_id = str(uuid.uuid4())
        cursor_obj = CursorMeta(
            data_list=data_list,
            cursor_id=cursor_id,
            page_number=math.floor((skip / limit) + 1) if asset_count else 0,
            asset_count=asset_count,
        )
        cursors[cursor_id] = cursor_obj
        return cursor_obj
    except Exception:
        logger.exception('Exception when finding cursor')
        raise


def get_db_projection(db_projection, sort):
    db_projection = dict(db_projection)
    _normalize_db_projection_for_aggregation(db_projection)
    if bool(sort):
        sort_path = list(sort)[0]
        field = '.'.join(sort_path.split('.')[2:])
        operator = None
        if f'specific_data.data.{field}' in MAX_SORTED_FIELDS:
            operator = '$max'
        elif f'specific_data.data.{field}' in MIN_SORTED_FIELDS:
            operator = '$min'
        if operator:
            db_projection['tempSortField'] = {
                operator:
                    {
                        '$map': {
                            'input': '$adapters.data', 'as': 'el', 'in': f'$$el.{field}'
                        }
                    }
            }
            sort = {'tempSortField': sort[sort_path]}
    return db_projection, sort


def _get_entities_raw(entity_type: EntityType,
                      view_filter: dict,
                      db_projection: dict = None,
                      limit: int = None,
                      skip: int = None,
                      sort: dict = None,
                      default_sort: bool = False,
                      history_date: datetime = None,
                      ) -> Iterator[dict]:
    """
    See get_entities for explanation of the parameters
    """
    if db_projection:
        db_projection, sort = get_db_projection(db_projection, sort)

    entity_views_db, is_date_filter_required = plugin_base_instance().get_appropriate_view(history_date, entity_type)
    # if we defaulted to normal history collection, add historized_filter
    if history_date and is_date_filter_required:
        view_filter = get_historized_filter(view_filter, history_date)
    try:
        yield from _perform_find(entity_views_db, limit, skip, view_filter, sort, db_projection, entity_type,
                                 default_sort)
    except PyMongoError:
        try:
            logger.warning('Find couldn\'t handle the weight! Going to slow path')
            yield from _perform_aggregation(entity_views_db,
                                            limit, skip, view_filter, sort,
                                            db_projection, entity_type,
                                            default_sort)
        except Exception:
            logger.exception('Exception when using perform aggregation')
            raise
    except Exception:
        logger.exception('Exception when using perform find')
        raise


def convert_entities_to_frontend_entities(data_list: Iterable[dict],
                                          projection: dict,
                                          ignore_errors: bool = False,
                                          include_details: bool = False,
                                          field_filters: dict = None,
                                          ) -> Iterable[dict]:
    """
    Converts db like entities to frontend accepted entities.
    See get_entities for parameters
    """
    for entity in data_list:
        entity = convert_db_entity_to_view_entity(entity, ignore_errors=ignore_errors)
        if not projection:
            yield nongui_beautify_db_entry(entity)
        else:
            yield parse_entity_fields(entity, projection.keys(), include_details=include_details,
                                      field_filters=field_filters)


# pylint: disable=R0913


def get_entities(limit: int,
                 skip: int,
                 view_filter: dict,
                 sort: dict,
                 projection: dict,
                 entity_type: EntityType,
                 default_sort: bool = True,
                 run_over_projection: bool = True,
                 history_date: datetime = None,
                 ignore_errors: bool = False,
                 include_details: bool = False,
                 field_filters: dict = None,
                 cursor_id: str = None,
                 use_cursor: bool = False,
                 ) -> Tuple[Iterable[dict], str]:
    """
    Get Axonius data of type <entity_type>, from the aggregator which is expected to store them.
    :param limit: the max amount of entities to return
    :param skip: use this only with a "sort" defined. skips a defined amount first - usually for pagination
    :param view_filter: a query to be queried for, that matches mongos's filter
    :param sort: a dict {name: pymongo.DESCENDING/ASCENDING, ...} to specify sort
    :param projection: a projection in mongo's format to project which fields are to be returned
    :param entity_type: Entity type to get
    :param default_sort: adds an optional default sort using ADAPTERS_LIST_LENGTH
    :param run_over_projection: adds some common fields to the projection
    :param history_date: the date for which to fetch, or None for latest
    :param ignore_errors: Passed to convert_db_entity_to_view_entity
    :param field_filters: Filter fields' values to those that are have a string including their matching filter
    :param use_cursor: whether to use cursor based pagination
    :param cursor_id: cursor_id for getting next results set
    :return:
    """
    if run_over_projection:
        for field in FIELDS_TO_PROJECT_FOR_GUI:
            if projection:
                projection[field] = 1

    db_projection = convert_db_projection_to_view(projection) or {}
    if run_over_projection or projection:
        for field in FIELDS_TO_PROJECT:
            db_projection[field] = 1

    logger.debug(f'Fetching data for entity {entity_type.name}')
    limit = limit or 0
    skip = skip or 0

    if use_cursor:
        cursor_obj = _get_all_entities_raw(
            entity_type=entity_type,
            view_filter=view_filter,
            db_projection=db_projection,
            cursor_id=cursor_id,
            sort=sort,
            skip=skip,
            limit=limit,
            default_sort=default_sort,
            history_date=history_date,
        )

        entities = convert_entities_to_frontend_entities(
            data_list=cursor_obj.data_list,
            projection=projection,
            ignore_errors=ignore_errors,
            include_details=include_details,
            field_filters=field_filters,
        )
        return entities, cursor_obj

    data_list = _get_entities_raw(
        entity_type=entity_type,
        view_filter=view_filter,
        db_projection=db_projection,
        limit=limit,
        skip=skip,
        sort=sort,
        default_sort=default_sort,
        history_date=history_date,
    )

    return convert_entities_to_frontend_entities(
        data_list=data_list,
        projection=projection,
        ignore_errors=ignore_errors,
        include_details=include_details,
        field_filters=field_filters,
    )


def perform_axonius_query(entity: EntityType,
                          query: str,
                          projection: dict = None,
                          skip: int = 0,
                          limit: int = 0,
                          sort: dict = None) -> Iterator[dict]:
    """
    Performs an axonius query language query on the DB
    :param entity: The entity type
    :param query: The query string, as seen in the entity table
    :param projection: Projection to db
    :param skip: additional parameter
    :param limit: additional parameter
    :param sort: additional parameter
    :return: an iterator for all the devices as they would been seen in the DB
    """
    return _get_entities_raw(entity, parse_filter(query), db_projection=projection, limit=limit, skip=skip, sort=sort)


def iterate_axonius_entities(entity: EntityType,
                             internal_axon_ids: Iterable[str],
                             **kwargs) -> Iterable[dict]:
    """
    Iterates on the DB on all given internal axon ids
    :param entity: The entity type
    :param internal_axon_ids: An interator of internal axon ids
    :param kwargs: additional parameters to each "find" request
    :return: an iterable for axonius entities as they appear in the db, with the kwargs applies on "find"
    """
    # pylint: disable=W0212
    collection = plugin_base_instance()._entity_db_map[entity]
    for chunk in chunks(ITERATE_CHUNK_SIZE, internal_axon_ids):
        yield from collection.find({
            'internal_axon_id': {
                '$in': chunk
            }
        }, **kwargs)


def perform_saved_view(entity: EntityType, saved_view: dict, **kwargs) -> Iterator[dict]:
    """
    Performs a saved view on the DB
    :param entity: The entity type
    :param saved_view: the saved view, as it is in the DB
    :param kwargs: additional parameters to "find"
    :return: an iterator for all the devices as they would been seen in the DB
    """
    parsed_query_filter = saved_view['view']['query']['filter']
    mongo_sort = get_sort(saved_view['view'])

    return perform_axonius_query(entity, parsed_query_filter,
                                 sort=mongo_sort, **kwargs)


def perform_saved_view_converted(entity: EntityType,
                                 saved_view: dict,
                                 projection: dict = None,
                                 run_over_projection: bool = True,
                                 **kwargs) -> Iterator[dict]:
    """
    Performs a saved view on the DB and converts the entities to GUI like form
    :param entity: The entity type
    :param saved_view: the saved view, as it is in the DB
    :param projection: override the view's projection
    :param run_over_projection: add projections for GUI
    :param kwargs: additional parameters to "find"
    :return: an iterator for all the devices as they would been seen in the DB
    """
    field_filters = saved_view['view'].get('colFilters', {})
    res = perform_saved_view(entity, saved_view, **kwargs)
    if projection and run_over_projection:
        for field in FIELDS_TO_PROJECT_FOR_GUI:
            if projection:
                projection[field] = 1
    if not projection:
        projection = {
            k: 1
            for k
            in saved_view['view']['fields']
        }
    return convert_entities_to_frontend_entities(res, projection, True, field_filters=field_filters)


def perform_saved_view_by_id(entity: EntityType,
                             saved_view_id: str,
                             **kwargs) -> Iterable[dict]:
    """
    Performs a saved view on the DB
    :param entity: The entity type
    :param saved_view_name: the name of saved view
    :param kwargs: additional parameters to "find"
    :raise ValueError: if the query doesn't exist
    :return: an iterator for all the devices as they would been seen in the DB
    """
    saved_view = plugin_base_instance().gui_dbs.entity_query_views_db_map[entity].find_one({
        '_id': ObjectId(saved_view_id)
    })
    if saved_view is None:
        raise ValueError(f'Missing query with id {saved_view_id}')
    return perform_saved_view(entity, saved_view, **kwargs)
