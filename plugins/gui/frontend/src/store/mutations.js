import { validModule } from './actions'
import { pluginMeta } from '../static'

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
	state[payload.module].data.view = { ...state[payload.module].data.view, ...payload.view }
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

export const UPDATE_DATA_FIELDS = 'UPDATE_DATA_FIELDS'
export const updateDataFields = (state, payload) => {
	if (!validModule(state, payload)) return
	const fields = state[payload.module].data.fields
	fields.fetching = payload.fetching
	fields.error = payload.error
	if (payload.data) {
		fields.data = { generic: payload.data.generic, specific: {}, schema: payload.data.schema}
		Object.keys(payload.data.specific).forEach((name) => {
			fields.data.specific[name] = payload.data.specific[name]
			fields.data.generic[0].items.enum.push({name, title: pluginMeta[name].title})
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