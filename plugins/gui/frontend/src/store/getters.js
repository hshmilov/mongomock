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
    return objectView ?
        schema.filter(field => field.items && Array.isArray(field.items)) :
        schema.filter(field => !field.items || !Array.isArray(field.items))
}

export const GET_DATA_SCHEMA_BY_NAME = 'GET_DATA_SCHEMA_BY_NAME'
export const getDataSchemaByName = (state) => (module) => {
    let fields = state[module].fields.data
    if (!fields.generic || !fields.generic.length) return []

    let allFieldsList = [...fields.generic]
    allFieldsList = Object.values(fields.specific).reduce((aggregatedList, currentList) => {
        return aggregatedList.concat(currentList)
    }, allFieldsList)

    return allFieldsList.reduce((map, schema) => {
        map[schema.name] = schema
        return map
    }, {})
}

export const GET_DATA_FIELD_LIST_SPREAD = 'GET_DATA_FIELD_LIST_SPREAD'
export const getDataFieldListSpread = (state) => (module) => {
    if (!state[module] || !state[module].fields || !state[module].fields.data) return []
    let fields = state[module].fields.data
    if (!fields.generic || !state[module].fields.data.generic.length) return []

    return fields.generic.filter((field) => {
        return !(field.type === 'array' && (Array.isArray(field.items) || field.items.type === 'array'))
    }).concat(Object.keys(fields.specific || []).reduce((list, name) => {
        if (!fields.specific[name]) return list
        list = [...list, ...fields.specific[name].map((field) => {
            if (singleAdapter(state)) return field
            return {...field, logo: name}
        })]
        return list
    }, []))
}

export const GET_DATA_BY_ID = 'GET_DATA_BY_ID'
export const getDataByID = (state) => (module) => {
    if (!state[module] || !state[module].content || !state[module].content.data
        || !state[module].current || !state[module].current.data) return []

    return state[module].content.data.reduce(function (map, input) {
        map[input['internal_axon_id']] = input
        return map
    }, {})
}

export const SINGLE_ADAPTER = 'SINGLE_ADAPTER'
export const singleAdapter = (state) => {
    if (!state.configuration || !state.configuration.data || !state.configuration.data.system) return false
    return state.configuration.data.system.singleAdapter
}

export const IS_EXPIRED = 'IS_EXPIRED'
export const isExpired = (state) => {
    return state.expired.data && state.auth.currentUser.data.user_name !== '_axonius'
}