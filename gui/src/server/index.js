const express = require('express')
const app = express()
var MongoClient = require('mongodb').MongoClient

const aggregatorDB = 'aggregator_plugin_52576'

app.get('/api/devices', function (req, res) {
  MongoClient.connect('mongodb://ax_user:ax_pass@localhost:27017', function (err, client) {
    if (err) throw err

    group_by = {'_id': '$data.id'}
    const fields = req.query['fields'] ? JSON.parse(req.query.fields) : 'all'
    if (fields == 'all') {
      group_by['all'] = {$first: '$$ROOT'}
    } else {
      fields.forEach(function (field) {
        group_by[field[0]] = {$first: '$' + field[1]}
      })
      group_by['date_fetcher'] = {$first: '$_id'}
    }
    group_by['Adapters'] = {$addToSet: '$plugin_name'}
    group_by['Tags'] = { $addToSet: '$tag' }
    const skip = req.query['skip'] ? parseInt(req.query.skip) : 0
    const limit = req.query['limit'] ? parseInt(req.query.limit) : 100
    console.log(`GET /devices with: fields=[${fields}] skip=${skip} limit=${limit}`)
    client.db(aggregatorDB).collection('parsed').aggregate([
      {$group: group_by},
      {$skip: skip},
      {$limit: limit}
    ]).toArray(function (err, result) {
      if (err) throw err

      res.header('Access-Control-Allow-Origin', '*')
      res.header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
      res.header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
      client.close()
      res.send(result)
    })
  })
})

app.post('/api/filters', function (req, res) {
  MongoClient.connect('mongodb://ax_user:ax_pass@localhost:27017', function (err, client) {
    if (err) throw err

    res.header('Access-Control-Allow-Origin', '*')
    res.header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    res.header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    console.log(`POST /filters with: name=${req['name']} query=${req['query']}`)
    client.db('queries').updateOne({'name': req['name']},
      {'name': req['name'], 'query': req['query']},
      function (err, result) {
        if (err) throw err

        client.close()
        res.send("")
      }
    )
  })
})

app.listen(3000, function () {
  console.log('Axonius server listening on port 8000!')
})