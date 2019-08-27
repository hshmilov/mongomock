import {pluginMeta} from '../constants/plugin_meta.js'

export const GET_DATA_FIELDS_BY_PLUGIN = 'GET_DATA_FIELDS_BY_PLUGIN'
export const getDataFieldsByPlugin = (state) => (module, objectView) => {
    if (!state[module] || !state[module].fields || !state[module].fields.data) return []
    let fields = state[module].fields.data
    if (!fields.generic || !fields.generic.length || (objectView && !fields.schema.generic)) return []

    return [
        {
            name: 'axonius', title: 'General', fields: selectFields(fields.generic, objectView)
        }, ...Object.keys(fields.specific).map((name) => {
            let title = pluginMeta[name] ? pluginMeta[name].title : name
            return {
                title, name, fields: selectFields(fields.specific[name], objectView)
            }
        }).sort((first, second) => {
            // Sort by adapters plugin name (the one that is shown in the gui).
            let firstText = first.title.toLowerCase()
            let secondText = second.title.toLowerCase()
            if (firstText < secondText) return -1
            if (firstText > secondText) return 1
            return 0
        })
    ]
}

const selectFields = (schema, objectView) => {
    return objectView
      ? schema.filter(field => field.items && !Array.isArray(field.items) && field.items.type === 'array')
      : schema
}

export const GET_DATA_SCHEMA_BY_NAME = 'GET_DATA_SCHEMA_BY_NAME'
export const getDataSchemaByName = (state) => (module) => {
    let fields = state[module].fields.data
    if (!fields.generic || !fields.generic.length) return []

    let allFieldsList = [...fields.generic]
    if (fields.specific) {
        allFieldsList = Object.values(fields.specific).reduce((aggregatedList, currentList) => {
            return aggregatedList.concat(currentList)
        }, allFieldsList)
    }

    return allFieldsList.reduce((map, schema) => {
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

export const IS_EXPIRED = 'IS_EXPIRED'
export const isExpired = (state) => {
    return state.expired.data && state.auth.currentUser.data.user_name !== '_axonius'
}