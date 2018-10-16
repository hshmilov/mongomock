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

rs.initiate(config)
