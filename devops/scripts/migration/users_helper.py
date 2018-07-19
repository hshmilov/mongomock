from services.plugins.mongo_service import MongoService
import argparse
import json
import sys


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['store', 'restore'])
    parser.add_argument("-f", "--file", default='/tmp/axonius_gui_users_hash', help="Hashed file location")
    try:
        args = parser.parse_args(args)
    except AttributeError:
        print(parser.usage())
        print('exiting')
        sys.exit(1)

    hashfile = args.file

    mongo = MongoService()
    users_collection = mongo.client['gui']['users']

    if args.mode == 'store':
        print('Saving users')
        users = list(users_collection.find(projection={'_id': 0}))
        with open(hashfile, 'wb') as hf:
            hf.write(json.dumps(users).encode())

    if args.mode == 'restore':
        print('Restoring users')
        with open(hashfile, 'rb') as hf:
            users = json.loads(hf.read())
            users_collection.remove({})
            users_collection.insert_many(users)


if __name__ == '__main__':
    main(sys.argv[1:])
