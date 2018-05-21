import { pluginMeta } from '../static.js'

export const GET_DATA_FIELD_LIST_TYPED = 'GET_DATA_FIELD_LIST_TYPED'
export const getDataFieldsListTyped = (state) => (module) => {
	if (!state[module] || !state[module].fields || !state[module].fields.data) return []
	let fields = state[module].fields.data
	if (!fields.generic || !state[module].fields.data.generic.length) return []

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
	if (!state[module] || !state[module].fields || !state[module].fields.data) return []
	let fields = state[module].fields.data
	if (!fields.generic || !state[module].fields.data.generic.length) return []

	return fields.generic.filter((field) => {
		return !(field.type === 'array' && (Array.isArray(field.items) || field.items.type === 'array'))
	}).concat(Object.keys(fields.specific || []).reduce((list, name) => {
		if (!fields.specific[name]) return list
		list = [...list, ...fields.specific[name].map((field) => {
			if (state.configurable.gui && state.configurable.gui.GuiService.config.system_settings.singleAdapter) return field
			return { ...field, logo: name}
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