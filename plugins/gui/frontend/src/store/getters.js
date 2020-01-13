import { pluginMeta } from '../constants/plugin_meta.js'
import { isObjectListField } from '../constants/utils'
import _get from 'lodash/get'
import _isEmpty from 'lodash/isEmpty'

export const GET_MODULE_SCHEMA = 'GET_MODULE_SCHEMA'
export const getModuleSchema = (state) => (module, objectView) => {
    const fields = _get(state[module], 'fields.data')
    if (_isEmpty(fields) || _isEmpty(fields.generic) ||  (objectView && _isEmpty(fields.schema))) {
        return []
    }
    const plugins = Object.keys(fields.specific).map((name) => {
        const title = pluginMeta[name] ? pluginMeta[name].title : name
        return { title, name }
    })
    return [{
        name: 'axonius',
        title: 'Aggregated',
        fields: selectFields(fields.generic, objectView),
        plugins
    }, ...plugins.map(plugin => {
        return {
            ...plugin,
            fields: selectFields(fields.specific[plugin.name], objectView)
        }
    }).sort((first, second) => {
        // Sort by adapters plugin name (the one that is shown in the gui).
        let firstText = first.title.toLowerCase()
        let secondText = second.title.toLowerCase()
        if (firstText < secondText) return -1
        if (firstText > secondText) return 1
        return 0
    })]
}

const selectFields = (schema, objectView) => {
    return objectView
        ? schema.filter(isObjectListField)
        : schema
}

export const GET_DATA_SCHEMA_LIST = 'GET_DATA_SCHEMA_LIST'
export const getDataSchemaList = (state) => (module) => {
    let fields = state[module].fields.data
    if (!fields.generic || !fields.generic.length) return []

    let allFieldsList = [...fields.generic]
    if (fields.specific) {
        allFieldsList = Object.entries(fields.specific).reduce((aggregatedList, [specificName, currentList]) => {
            currentList.map(field => field.logo = (singleAdapter(state) ? undefined : specificName))
            return aggregatedList.concat(currentList)
        }, allFieldsList)
    }
    return allFieldsList
}

export const GET_DATA_SCHEMA_BY_NAME = 'GET_DATA_SCHEMA_BY_NAME'
export const getDataSchemaByName = (state) => (module) => {
    return getDataSchemaList(state)(module).reduce((map, schema) => {
        map[schema.name] = schema
        return map
    }, {})
}

export const SINGLE_ADAPTER = 'SINGLE_ADAPTER'
export const singleAdapter = (state) => {
    if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return false
    return state.configuration.data.system.singleAdapter
}

export const AUTO_QUERY = 'AUTO_QUERY'
export const autoQuery = (state) => {
    if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return true
    return state.configuration.data.system.autoQuery
}

export const EXACT_SEARCH = 'EXACT_SEARCH'
export const exactSearch = (state) => {
    if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return false
    return state.configuration.data.system.exactSearch
}


export const IS_EXPIRED = 'IS_EXPIRED'
export const isExpired = (state) => {
    return state.expired.data && state.auth.currentUser.data.user_name !== '_axonius'
}

export const GET_CONNECTION_LABEL = 'GET_CONNECTION_LABEL'
export const getConnectionLabel = (state) => (clientId, adapterName) => {
    // extract the connection label saved in client config
    // get the clientId and adapter name to find the client config in state
    const adaptersClients = state.adapters.clients
    const currentClient = adaptersClients.find( item => item['adapter_name'] === adapterName
                                                        && item['client_id'] === clientId )
    if ( !currentClient ) return ''
    const connectionLabel = currentClient['client_config']['connection_label']
    if ( !connectionLabel ) return ''
    return ` - ${connectionLabel}`
}

const savedQueries = (state, namespace) => {
    const data =  state[namespace].views.saved.content.data || []
    return data.filter(view => view)
}

export const getSavedQueryById = (state) => (id, namespace) => {
    return savedQueries(state, namespace).find(q => id === q.uuid)
}


export const configuredAdaptersFields = (state) => (entity) => {

    // entity can be 'devices' either 'users'
    const entityState = state[entity]
    
    const genericFields = entityState.fields.data.generic.map(f => f.name)
    const adaptersSpecificFields = entityState.fields.data.specific

    const configuredAdaptesSchemas = Object.values(adaptersSpecificFields)
    const specificFields = configuredAdaptesSchemas.reduce((fields, currentAdaptersFields) => {
        return [
            ...fields,
            ...currentAdaptersFields.map(field => field.name)
        ]
    }, [])

    return new Set([...genericFields, ...specificFields])
}
