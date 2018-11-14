from pymongo.collection import Collection
from pymongo.errors import CollectionInvalid, OperationFailure


def get_collection_stats(col: Collection):
    """
    Gets the collection stats
    https://docs.mongodb.com/manual/reference/method/db.collection.stats/
    """
    return col.database.command('collstats', col.name)


def get_collection_storage_size(col: Collection):
    """
    Returns the collections storage size on disk in bytes
    :param col: pymongo collection
    :return: size in bytes
    """
    try:
        col_stats = get_collection_stats(col)
        return col_stats['storageSize']
    except OperationFailure:
        # If the collection doesn't exist this is the exception received
        return 0


def get_collection_capped_size(col: Collection) -> int:
    """
    If the collection is capped, return its size in bytes. Otherwise return None
    """
    options = col.options()
    if options.get('capped'):
        return options['size']
    return None


def create_capped_collection(col: Collection, size):
    """
    Creates a capped collection with the given size.
    If the collection is already capped, resize to the given size.
    :param col: the collection to cap
    :param size: the size of the collection, in bytes
    :return:
    """
    try:
        col.database.create_collection(col.name, capped=True, size=size)
    except CollectionInvalid:
        # this is raised if the collection already exists
        col.database.command({
            'convertToCapped': col.name,
            'size': size
        })


def set_mongo_parameter(connection, name, value):
    """
    Sets a mongo value
    :param connection: db connection
    :param name: value name
    :param value: the value to set
    """
    connection['admin'].command({
        'setParameter': 1,
        name: value
    })


def truncate_capped_collection(col: Collection):
    """
    Mongo is not the most feature rich DB out there.
    This drops the collection, then creates it with the same cap and reinstalls all indexes it previously had.
    :param col: the collection to recreate
    """
    size = get_collection_capped_size(col)
    index_information = col.index_information()
    col.drop()

    if size is not None:
        create_capped_collection(col, size)

    for index in index_information.values():
        col.create_index(index['key'])
