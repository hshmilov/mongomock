import pymongo
import requests

# Read this https://axonius.atlassian.net/wiki/spaces/AX/pages/643334161/HTTPS+infrastructure+used
# pylint: disable=invalid-name
original_request = requests.Session.request


# for now - no verification
# AX-1591: Use our own CA here and create specific certificates for each plugin
def __request(*args, **kwargs):
    # Some plugins pass 'verify' in args and not kwargs. In the current requests version, its the 14th param, so we
    # have to check this in the following code, to force verify to be False only if it is not set already.
    if 'verify' not in kwargs and len(args) < 14:
        kwargs['verify'] = False
    return original_request(*args, **kwargs)


# Monkey-patching
requests.Session.request = __request


# PyMongo doesn't allow the following pattern out of the box:
# with collection.start_session() as session:
#     with session.start_transaction():
#         session.insert_one({})
#         session.delete_one({})
#         ...
# it wants you to pass `session` each time you want to make an operation, like this:
# with collection.start_session() as session:
#     with session.start_transaction():
#         collection.insert_one({}, session=session)
#         collection.delete_one({}, session=session)
#         ...
# notice that in the first example I had SESSION.OPERATION(...)
# and in the second example I Had COLLECTION.OPERATION(..., session=SESSION)
# if you forget to pass session=session than the operation will take place outside the transaction
# which in my honest opinion is bug prone, so I've added this monkey addition to allow for the first pattern.

def start_session(self: pymongo.collection.Collection):
    session = self.database.client.start_session()
    for name in dir(pymongo.collection.Collection):
        if not name.startswith('_') and not hasattr(session, name):
            val = getattr(pymongo.collection.Collection, name)

            if callable(val):
                def create_function(collection_respective_method):
                    def session_function_wrapper(*args, **kwargs):
                        return collection_respective_method(self, *args, **kwargs, session=session)
                    return session_function_wrapper

                setattr(session, name, create_function(val))
    return session


pymongo.collection.Collection.start_session = start_session
