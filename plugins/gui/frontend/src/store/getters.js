import { pluginMeta } from '../static.js'

export const GET_DATA_FIELD_LIST_TYPED = 'GET_DATA_FIELD_LIST_TYPED'
export const getDataFieldsListTyped = (state) => (module) => {
	if (!state[module] || !state[module].data.fields || !state[module].data.fields.data) return []
	let fields = state[module].data.fields.data
	if (!fields.generic || !state[module].data.fields.data.generic.length) return []

	return [
		{
			name: 'axonius', title: 'General', fields: fields.generic
		},
		...Object.keys(fields.specific).map((name) => {
			let title = pluginMeta[name] ? pluginMeta[name].title : name
			return { title, name, fields: fields.specific[name] }
		})
	]
}

export const GET_DATA_FIELD_LIST_SPREAD = 'GET_DATA_FIELD_LIST_SPREAD'
export const getDataFieldListSpread =  (state) => (module) => {
	if (!state[module] || !state[module].data.fields || !state[module].data.fields.data) return []
	let fields = state[module].data.fields.data
	if (!fields.generic || !state[module].data.fields.data.generic.length) return []

	return fields.generic.filter((field) => {
		return !(field.type === 'array' && (Array.isArray(field.items) || field.items.type === 'array'))
	}).concat(Object.keys(fields.specific).reduce((list, name) => {
		if (!fields.specific[name]) return list
		list = [...list, ...fields.specific[name].map((field) => {
			if (state['settings'].data.singleAdapter) return field
			return { ...field, logo: name}
		})]
		return list
	}, []))
}