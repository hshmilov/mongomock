db = new Mongo('localhost:27017').getDB('admin')

db.auth('ax_user','ax_pass')

config = {
    "_id" : "axon-cluster",
    "members" : [
        {
            "_id" : 0,
            "host" : "mongo:27017"
        }
    ]
  }

res = rs.initiate(config)
print('Configured replica set:')
printjson(res)

slept = 0;
while(rs.status().ok != 1 || db.isMaster().ismaster != true) {
    print('Waiting for replica set to be ready...');
    printjson(rs.status());
    sleep(500);
    slept += 500;

    // wait for 120 seconds.
    if (slept == 1000 * 120) {
        throw 'Replica set initialization failed!';
    }
}