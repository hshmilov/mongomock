import { validModule } from './actions'
import { pluginMeta } from '../static'

export const TOGGLE_SIDEBAR = 'TOGGLE_SIDEBAR'
export const toggleSidebar = (state) => {
    state.interaction.collapseSidebar = !state.interaction.collapseSidebar
}

export const UPDATE_EMPTY_STATE = 'TOGGLE_EMPTY_STATE'
export const updateEmptyState = (state, payload) => {
	state.interaction.onboarding.emptyStates[payload.name] = payload.status
}

export const UPDATE_DATA_COUNT = 'UPDATE_DATA_COUNT'
export const updateDataCount = (state, payload) => {
	if (!validModule(state, payload)) return
	const count = state[payload.module].count
	count.fetching = payload.fetching
	count.error = payload.error
	if (payload.data !== undefined) {
		count.data = payload.data
	}
}

export const UPDATE_DATA_CONTENT = 'UPDATE_DATA_CONTENT'
export const updateDataContent = (state, payload) => {
	if (!validModule(state, payload)) return
	const content = state[payload.module].content
	if (content.fetching && !payload.fetching && content.rule !== payload.rule) {
		return
	}

	content.fetching = payload.fetching
	content.rule = payload.rule
	content.error = payload.error
	if (payload.data) {
		content.data = payload.data
	}
}

export const UPDATE_DATA_VIEW = 'UPDATE_DATA_VIEW'
export const updateDataView = (state, payload) => {
	if (!validModule(state, payload)) return
	state[payload.module].view = { ...state[payload.module].view, ...payload.view }
}

export const UPDATE_DATA_VIEWS = 'UPDATE_DATA_VIEWS'
export const updateDataViews = (state, payload) => {
	if (!validModule(state, payload)) return
	const views = state[payload.module].views
	views.fetching = payload.fetching
	views.error = payload.error
	if (payload.data) {
		views.data = payload.data
	}
}

export const ADD_DATA_VIEW = 'ADD_DATA_VIEW'
export const addDataView = (state, payload) => {
	if (!validModule(state, payload)) return
	const views = state[payload.module].views
	if (!views.data) views.data = []
	views.data = [{ name: payload.name, view: payload.view }, ...views.data.filter(item => item.name !== payload.name)]
}

export const UPDATE_DATA_FIELDS = 'UPDATE_DATA_FIELDS'
export const updateDataFields = (state, payload) => {
	if (!validModule(state, payload)) return
	const fields = state[payload.module].fields
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
	const queries = state[payload.module].queries[payload.type]
	queries.fetching = payload.fetching
	queries.error = payload.error
	if (payload.data) {
		queries.data = queries.data.slice(0, payload.skip).concat(payload.data)
	}
}

export const ADD_DATA_QUERY = 'ADD_DATA_QUERY'
export const addDataQuery = (state, payload) => {
	if (!validModule(state, payload)) return
	const savedQueries = state[payload.module].queries.saved
	if (!savedQueries.data) savedQueries.data = []
	savedQueries.data = [
		{ ...payload.query, timestamp: new Date() },
		...savedQueries.data.filter(item => item.name !== payload.query.name)
	]
}

export const UPDATE_REMOVED_DATA_QUERY = 'UPDATE_REMOVED_DATA_QUERY'
export const updateRemovedDataQuery = (state, payload) => {
	if (!validModule(state, payload)) return

	state[payload.module].queries.saved.data =
		state[payload.module].queries.saved.data.filter(query => !payload.ids.includes(query.uuid))
}

export const UPDATE_DATA_LABELS = 'UPDATE_DATA_LABELS'
export const updateDataLabels = (state, payload) => {
	if (!validModule(state, payload)) return
	const labels = state[payload.module].labels
	labels.fetching = payload.fetching
	labels.error = payload.error
	if (payload.data) {
		labels.data = payload.data.map((label) => {
			return { name: label, title: label}
		})
	}
}

export const UPDATE_ADDED_DATA_LABELS = 'UPDATE_ADDED_DATA_LABELS'
export const updateAddedDataLabels = (state, payload) => {
	if (!validModule(state, payload)) return
	let data = payload.data
	state[payload.module].labels.data = state[payload.module].labels.data
		.filter(label => !data.labels.includes(label.name))
		.concat(data.labels.map((label) => {
			return {name: label, title: label}
		}))

	let content = [...state[payload.module].content.data]
	content.forEach(function (entity) {
		if (!data.entities.includes(entity.internal_axon_id)) return
		if (!entity.labels) entity.labels = []

		entity.labels = Array.from(new Set([ ...entity.labels, ...data.labels ]))
	})
	state[payload.module].content.data = content

	let current = state[payload.module].current.data
	if (current && current.internal_axon_id && data.entities.includes(current.internal_axon_id)) {
		state[payload.module].current.data = { ...current,
			labels: Array.from(new Set([ ...current.labels, ...data.labels]))
		}
	}
}

export const UPDATE_REMOVED_DATA_LABELS = 'UPDATE_REMOVED_DATA_LABELS'
export const updateRemovedDataLabels = (state, payload) => {
	if (!validModule(state, payload)) return
	let data = payload.data
	state[payload.module].labels.data = state[payload.module].labels.data.filter((label) => {
		if (!data.labels.includes(label.name)) return true
		let exists = false
		state[payload.module].content.data.forEach((entity) => {
			if (!entity.labels) return
			exists = exists && entity.labels.includes(label.name)
		})
		return exists
	})

	let content = [...state[payload.module].content.data]
	content.forEach((entity) => {
		if (!data.entities.includes(entity.internal_axon_id)) return
		if (!entity.labels) { return }
		entity.labels = entity.labels.filter((label) => !data.labels.includes(label))
	})
	state[payload.module].content.data = content

	let current = state[payload.module].current.data
	if (current && current.internal_axon_id && data.entities.includes(current.internal_axon_id) && current.labels) {
		state[payload.module].current.data = { ...current,
			labels: current.labels.filter((label) => !data.labels.includes(label))
		}
	}
}

export const UPDATE_DATA_BY_ID = 'UPDATE_DATA_BY_ID'
export const updateDataByID = (state, payload) => {
	if (!validModule(state, payload)) return
	const current = state[payload.module].current
	current.fetching = payload.fetching
	current.error = payload.error
	if (payload.data) {
		current.data = payload.data
	}
}