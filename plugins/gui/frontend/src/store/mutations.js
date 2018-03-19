
import { validModule } from './actions'

export const TOGGLE_SIDEBAR = 'TOGGLE_SIDEBAR'
export const toggleSidebar = (state) => {
    state.interaction.collapseSidebar = !state.interaction.collapseSidebar
}


export const UPDATE_DATA_COUNT = 'UPDATE_DATA_COUNT'
export const updateDataCount = (state, payload) => {
	if (!validModule(state, payload)) return
	const count = state[payload.module].data.count
	count.fetching = payload.fetching
	count.error = payload.error
	if (payload.data !== undefined) {
		count.data = payload.data
	}
}

export const UPDATE_DATA_CONTENT = 'UPDATE_DATA_CONTENT'
export const updateDataContent = (state, payload) => {
	if (!validModule(state, payload)) return
	const content = state[payload.module].data.content
	content.fetching = payload.fetching
	content.error = payload.error
	if (payload.data) {
		content.data = content.data.slice(0, payload.skip).concat(payload.data)
	}
}

export const UPDATE_DATA_VIEW = 'UPDATE_DATA_VIEW'
export const updateDataView = (state, payload) => {
	if (!validModule(state, payload)) return
	let data = state[payload.module].data
	data.view = { ...state[payload.module].data.view, ...payload.view }
}

export const UPDATE_DATA_VIEWS = 'UPDATE_DATA_VIEWS'
export const updateDataViews = (state, payload) => {
	if (!validModule(state, payload)) return
	const views = state[payload.module].data.views
	views.fetching = payload.fetching
	views.error = payload.error
	if (payload.data) {
		views.data = payload.data
	}
}

export const ADD_DATA_VIEW = 'ADD_DATA_VIEW'
export const addDataView = (state, payload) => {
	if (!validModule(state, payload)) return
	const views = state[payload.module].data.views
	if (!views.data) views.data = []
	views.data = [{ name: payload.name, view: payload.view }, ...views.data.filter(item => item.name !== payload.name)]
}

const flattenSchema = (schema, name = '') => {
	/*
		Recursion over schema to extract a flat map from field path to its schema
	 */
	if (schema.name) {
		name = name ? `${name}.${schema.name}` : schema.name
	}
	if (schema.type === 'array' && schema.items) {
		if (!Array.isArray(schema.items)) {
			if (schema.items.type !== 'array') {
				if (!schema.title) return []
				return [{...schema, name}]
			}
			let childSchema = {...schema.items}
			if (schema.title) {
				childSchema.title = childSchema.title ? `${schema.title} ${childSchema.title}` : schema.title
			}
			return flattenSchema(childSchema, name)
		}
		let children = []
		schema.items.forEach((item) => {
			children = children.concat(flattenSchema({...item}, name))
		})
		return children
	}
	if (!schema.title) return []
	return [{...schema, name}]
}

export const UPDATE_DATA_FIELDS = 'UPDATE_DATA_FIELDS'
export const updateDataFields = (state, payload) => {
	if (!validModule(state, payload)) return
	const fields = state[payload.module].data.fields
	fields.fetching = payload.fetching
	fields.error = payload.error
	if (payload.data) {
		fields.data = {generic: flattenSchema({ ...payload.data.generic, name: 'specific_data.data' }), specific: {}}
		Object.keys(payload.data.specific).forEach((name) => {
			fields.data.specific[name] = flattenSchema({ ...payload.data.specific[name], name: `adapters_data.${name}`})
		})
	}
}

export const UPDATE_DATA_QUERIES = 'UPDATE_DATA_QUERIES'
export const updateDataQueries = (state, payload) => {
	if (!validModule(state, payload) || !payload.type) return
	const queries = state[payload.module].data.queries[payload.type]
	queries.fetching = payload.fetching
	queries.error = payload.error
	if (payload.data) {
		queries.data = queries.data.slice(0, payload.skip).concat(payload.data)
	}
}

export const ADD_DATA_QUERY = 'ADD_DATA_QUERY'
export const addDataQuery = (state, payload) => {
	if (!validModule(state, payload)) return
	const savedQueries = state[payload.module].data.queries.saved
	if (!savedQueries.data) savedQueries.data = []
	savedQueries.data = [
		{ ...payload.query, timestamp: new Date() },
		...savedQueries.data.filter(item => item.name !== payload.query.name)
	]
}