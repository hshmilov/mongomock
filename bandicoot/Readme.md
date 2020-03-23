# Bandicoot 

## What is bandicoot?

Bandicoot is a Go service that migrates data from Mongodb to Postgresql serving it over a GraphQL API. 

- **Schema first** — Define your API using the GraphQL [Schema Definition Language](http://graphql.org/learn/schema/).
- **Performance** — Written in Golang, Bandicoot is written to be fast and highly optimized.
- **SQL** — Postgres under the hood.

## How to use Bandicoot in Axonius

To get a working system running in version run the following steps:
1. Have an axonius system up
2. ./axonius.sh service postgres up 
3. ./axonius.sh service bandicoot up
4. Run discovery on the axonius system, that will be transfered
5. Access GraphQL playground on port 9090

## How To Use Bandicoot as standalone

To get Bandicoot to run as a standalone system
1. use the make file to build postgres make postgres VERSION=latest
2. docker-compose up inside deployments/docker (starts postgres + pgadmin)
3. make serve / run the code from your IDE, configure arguments as required
4. Access GraphQL playground


## Getting Started

First if you don't know golang, work your way through the [Tutorial](https://tour.golang.org/welcome/1),
then get acquainted with gqlgen's [Getting Started](https://gqlgen.com/getting-started/) tutorial.

## Reporting Issues

If you think you've found a bug, or something isn't behaving the way you think it should, please raise an issue on GitHub.

## Query API

The query API is influenced by Hasura and Prisma's graphql API, but bandicoot supports some 
extra cutting edge features such as jsonpath filtering.

Query example:
```graphql
query {
  devices(
    where: {
      AND: [
        { lastSeen_gt:  1575996606000}
        {
          adapterDevices: {
            adapterId_eq: 3
            lastSeen_gt: 1552702531534
          }
        }
      ]
    },
    limit: 100
  ) {
    lastSeen
    adapterDevices {
      hostname
    }
  }
}
```