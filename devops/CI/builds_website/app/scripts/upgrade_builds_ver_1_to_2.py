import pymongo
import sys


def main():
    try:
        _, db_pass = sys.argv
    except Exception:
        print(f'Usage: {sys.argv[0]} [pass_to_db]')
        return -1

    print(f'Trying to connect to mongo..')
    db = pymongo.MongoClient(
        'mongo',
        username='axonius',
        password=db_pass,
        connect=False
    ).builds

    print(f'Connected..')
    for i, instance in enumerate(db.instances.find({})):
        if instance.get('ec2_id'):
            instance['id'] = instance['ec2_id']
            if not instance.get('cloud'):
                instance['cloud'] = 'aws'
            print(f'{i} Upgrading {instance["ec2_id"]}...')
            db.instances.update_one({'_id': instance['_id']}, {'$set': instance})

    print(f'Done')


if __name__ == '__main__':
    sys.exit(main())
