# pylint: disable=invalid-triple-quote
QUERY_DEVICES = """
query($after: Cursor, $limit: Int!, $sortOrder: SortOrder) {
  entities(archived: false
           types: [ENDPOINT]
           after: $after
           first: $limit
           sortOrder: $sortOrder) {
    nodes {
      primaryDisplayName
      secondaryDisplayName
      isServer: hasRole(type: ServerRole)

      ... on EndpointEntity
      {
        hostName
        lastIpAddress
        staticIpAddresses
        mostRecentActivity
        associations(bindingTypes: [OWNERSHIP, LOGIN, ACTIVITY_ORIGIN LOCAL_ADMINISTRATOR])
        {
          bindingType
          ... on EntityAssociation {
            entity
            {
              type
              primaryDisplayName
              isAdmin: hasRole(type: AdminAccountRole)
              isHuman: hasRole(type: HumanUserAccountRole)
              isProgrammatic: hasRole(type: ProgrammaticUserAccountRole)
            }
          }
        }
        riskScore
        riskScoreSeverity
        riskFactors {
          type
          severity
        }

        latestIncidents: openIncidents(first: 5, sortKey: END_TIME)
        {
          nodes
          {
            type
            startTime
            endTime
            compromisedEntities
            {
              primaryDisplayName
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}"""

QUERY_DEVICES_2 = """
query($after: Cursor, $limit: Int!, $sortOrder: SortOrder) {
  entities(archived: false
           types: [ENDPOINT]
           after: $after
           first: $limit
           sortOrder: $sortOrder) {
    nodes {
      primaryDisplayName
      secondaryDisplayName
      isServer: hasRole(type: ServerRole)

      ... on EndpointEntity
      {
        hostName
        lastIpAddress
        staticIpAddresses
        mostRecentActivity
        associations(bindingTypes: [OWNERSHIP, LOGIN, ACTIVITY_ORIGIN])
        {
          bindingType
          ... on EntityAssociation {
            entity
            {
              type
              primaryDisplayName
              isAdmin: hasRole(type: AdminAccountRole)
              isHuman: hasRole(type: HumanUserAccountRole)
              isProgrammatic: hasRole(type: ProgrammaticUserAccountRole)
            }
          }
        }
        riskScore
        riskScoreSeverity
        riskFactors {
          type
          severity
        }

        latestIncidents: openIncidents(first: 5, sortKey: END_TIME)
        {
          nodes
          {
            type
            startTime
            endTime
            compromisedEntities
            {
              primaryDisplayName
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}"""

QUERY_USERS = """
query($after: Cursor, $limit: Int!, $sortOrder: SortOrder) {
  entities(types: [USER], roles: [ProgrammaticUserAccountRole],
  after: $after
  first: $limit
  sortOrder: $sortOrder) {
    nodes {
      primaryDisplayName
      secondaryDisplayName
      isAdmin: hasRole(type: AdminAccountRole)
      isProgrammatic: hasRole(type: ProgrammaticUserAccountRole)
      accounts {
        ... on ActiveDirectoryAccountDescriptor {
          samAccountName
          domain
        }
      }
      ... on UserEntity {
        mostRecentActivity
        emailAddresses
        phoneNumbers
      }
      riskScore
      riskScoreSeverity
      riskFactors {
        type
        severity
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}

"""
