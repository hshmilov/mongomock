db.createRole({
     role: "insert_notification",
     privileges: [{resource: {db: "core", collection: "notifications"}, actions: ["insert"]}],
     roles: []
 });