from typing import Iterable

from bson import ObjectId
from funcy import chunks
from pymongo import ASCENDING
from pymongo.collection import Collection


def insert_chunked(collection: Collection, chunk_size: int, data: Iterable[object]) -> ObjectId:
    """
    Inserts the given list into the DB in a paginated form, and returns the group id of the chunk
    """
    result = None
    chunk_group_id = ObjectId()
    for chunk_number, chunk in enumerate(chunks(chunk_size, data)):
        chunk = list(chunk)
        obj = {
            # the chunked data
            'chunk': chunk,
            # the index of the current chunk
            'chunk_number': chunk,
            # the amount of data in the chunk
            'count': len(chunk),
            # the next chunk's _id
            'next': result.inserted_id if result else None,
            # the group id of the chunk, this is the same for all chunks in the same blob
            'chunk_group_id': chunk_group_id
        }
        result = collection.insert_one(obj)
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
