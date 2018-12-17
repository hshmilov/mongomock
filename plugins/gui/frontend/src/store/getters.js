import {pluginMeta} from '../constants/plugin_meta.js'

export const GET_DATA_FIELDS_BY_PLUGIN = 'GET_DATA_FIELDS_BY_PLUGIN'
export const getDataFieldsByPlugin = (state) => (module, objectView) => {
    if (!state[module] || !state[module].fields || !state[module].fields.data) return []
    let fields = state[module].fields.data
    if (!fields.generic || !fields.generic.length || (objectView && !fields.schema.generic)) return []

    return [
        {
            name: 'axonius', title: 'General', fields: objectView ?
                prepareSchemaObjects(fields.schema.generic, 'specific_data.data') :
                fields.generic
        }, ...Object.keys(fields.specific).map((name) => {
            let title = pluginMeta[name] ? pluginMeta[name].title : name
            return {
                title, name, fields: objectView ?
                    prepareSchemaObjects(fields.schema.specific[name], 'adapters_data.data') :
                    fields.specific[name]
            }
        }).sort((first, second) => {
            // Sort by adapter plugin name (the one that is shown in the gui).
            let firstText = first.title.toLowerCase()
            let secondText = second.title.toLowerCase()
            if (firstText < secondText) return -1
            if (firstText > secondText) return 1
            return 0
        })
    ]
}

const prepareSchemaObjects = (schema, prefix) => {
    // return flattenSchemaNames(schema, prefix).items.filter(item => item.type === 'object')
    return schema.items
        .filter(item => (item.type === 'array' && (Array.isArray(item.items) || item.items.type === 'array')))
        .map(item => {
            return { ...item,
                name: `${prefix}.${item.name}`,
                // If this is a list of objects, take the definition of the object
                items: item.items.type === 'array' ? item.items.items : item.items
            }
        })
}

const flattenSchemaNames = (schema, prefix) => {
    let name = schema.name ? `${prefix}.${schema.name}` : prefix
    if (schema.type !== 'array' || (!Array.isArray(schema.items) && schema.items.type !== 'array')) {
        return {...schema, name}
    }
    if (schema.items.type === 'array') {
        schema.items = schema.items.items
    }
    return {
        ...schema,
        name, type: 'object',
        items: schema.items.map(item => flattenSchemaNames(item, name))
    }
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