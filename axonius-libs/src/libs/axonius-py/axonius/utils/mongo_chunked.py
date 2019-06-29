import logging
from typing import Iterable, Tuple

from bson import ObjectId
from funcy import take
from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.errors import DocumentTooLarge

logger = logging.getLogger(f'axonius.{__name__}')


def _insert_chunked_internal(collection: Collection,
                             chunk: list,
                             chunk_number: int,
                             next_chunk: ObjectId,
                             chunk_group_id: ObjectId) -> Tuple[int, int, ObjectId]:
    """
    Internal insert chunked data. Handles DocumentTooLarge from the db by halving the chunk size.
    This method, compared to insert_chunked, assumes data as a list and not an iterator.
    :param collection: the collection to insert to
    :param chunk: the data to insert
    :param chunk_number: the current chunk number to start from
    :param next_chunk: the next chunk's id
    :param chunk_group_id: the chunk group id
    :return: (chunk_number, chunk_size, next_chunk) - current chunk number, current chunk size, last chunk's id
    """
    chunk_size = len(chunk)
    already_in = 0
    while already_in < len(chunk):
        try:
            to_insert = chunk[already_in: already_in + chunk_size]
            obj = {
                # the chunked data
                'chunk': to_insert,
                # the index of the current chunk
                'chunk_number': chunk_number,
                # the amount of data in the chunk
                'count': len(to_insert),
                # the next chunk's _id
                'next': next_chunk,
                # the group id of the chunk, this is the same for all chunks in the same blob
                'chunk_group_id': chunk_group_id
            }
            next_chunk = collection.insert_one(obj).inserted_id
            chunk_number += 1
            already_in += len(to_insert)
        except DocumentTooLarge as e:
            logger.debug(f'Chunk size {chunk_size} too large, trying to halve chunk size: {e}')
            if chunk_size == 1:
                logger.exception('Can not halve chunk size because it is 1!')
                raise
            chunk_size //= 2

    return chunk_number, chunk_size, next_chunk


def insert_chunked(collection: Collection, chunk_size: int, data: Iterable[object]) -> ObjectId:
    """
    Inserts the given list into the DB in a paginated form, and returns the group id of the chunk
    """
    result = None
    chunk_group_id = ObjectId()
    chunk_number = 0

    # if data is not an iterator, we make it one
    data = iter(data)

    while True:
        chunk = take(chunk_size, data)
        if not chunk:
            break
        chunk_number, chunk_size, result = _insert_chunked_internal(collection,
                                                                    chunk,
                                                                    chunk_number,
                                                                    result,
                                                                    chunk_group_id)
    return chunk_group_id if result else None


def read_chunked(collection: Collection, id_: ObjectId, projection=None) -> Iterable[object]:
    """
    Gets an iterator for the list from using the group id of the chunk given
    """
    if not id_:
        return

    if projection:
        projection = {**projection, **{
            'chunk': 1,
            'next': 1
        }}
    else:
        projection = {
            'chunk': 1,
            'next': 1
        }

    def get_res_and_next(id_to_get):
        result = collection.find_one({
            '_id': id_to_get
        }, projection=projection)
        return result['chunk'], result.get('next')

    first = collection.find_one({
        'chunk_group_id': id_
    }, projection=projection)
    yield from first['chunk']

    id_ = first.get('next')

    while id_:
        res, id_ = get_res_and_next(id_)
        yield from res


def get_chunks_length(collection: Collection, id_: ObjectId) -> int:
    """
    Gets just the length for the list for the group id of the chunk given
    """
    if not id_:
        return 0

    projection = {
        'count': 1,
        'next': 1
    }

    def get_res_and_next(id_to_get):
        result = collection.find_one({
            '_id': id_to_get
        }, projection=projection)
        return result['count'], result.get('next')

    first = collection.find_one({
        'chunk_group_id': id_
    }, projection=projection)
    total = first['count']

    id_ = first.get('next')

    while id_:
        count, id_ = get_res_and_next(id_)
        total += count

    return total


def get_groups_by_filter(collection: Collection, mongo_filter: dict) -> Iterable[ObjectId]:
    """
    Gets all group ids that the filter given applies to any of their datas
    """
    return collection.distinct('chunk_group_id',
                               {
                                   'chunk': {
                                       '$elemMatch': mongo_filter
                                   }
                               })


def create_indexes_on_collection(collection: Collection):
    """
    Creates the necessary indexes on the collection that will be used for chunked content
    """
    collection.create_index([('chunk_group_id', ASCENDING)])
