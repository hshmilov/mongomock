import { getModule } from './actions'
import { pluginMeta } from '../constants/plugin_meta'

export const TOGGLE_SIDEBAR = 'TOGGLE_SIDEBAR'
export const toggleSidebar = (state) => {
    state.interaction.collapseSidebar = !state.interaction.collapseSidebar
}

export const UPDATE_WINDOW_WIDTH = 'UPDATE_WINDOW_WIDTH'
export const updateWindowWidth = (state) => {
	state.interaction.windowWidth = document.documentElement.clientWidth
}

export const UPDATE_DATA_COUNT = 'UPDATE_DATA_COUNT'
export const updateDataCount = (state, payload) => {
	let module = getModule(state, payload)
	if (!module) return
	const count = module.count
	if (!payload.fetching && count.rule !== payload.rule) {
		return
	}
	count.fetching = payload.fetching
	count.error = payload.error
	count.rule = payload.rule
	if (payload.data !== undefined) {
		count.data = payload.data
	}
}

export const UPDATE_DATA_CONTENT = 'UPDATE_DATA_CONTENT'
export const updateDataContent = (state, payload) => {
	let module = getModule(state, payload)
	if (!module) return
	const content = module.content
	if (!payload.fetching && content.rule !== payload.rule) {
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
	let module = getModule(state, payload)
	if (!module) return
    if (module.view.query && payload.view.query && module.view.query.filter !== payload.view.query.filter) {
        module.content.data = []
    }
	module.view = { ...module.view, ...payload.view }
}

export const UPDATE_DATA_VIEWS = 'UPDATE_DATA_VIEWS'
export const updateDataViews = (state, payload) => {
	if (!getModule(state, payload)) return
	const views = state[payload.module].views[payload.type]
	views.fetching = payload.fetching
	views.error = payload.error
	if (payload.data) {
		views.data = views.data.slice(0, payload.skip).concat(payload.data)
	}
}

export const ADD_DATA_VIEW = 'ADD_DATA_VIEW'
export const addDataView = (state, payload) => {
	if (!getModule(state, payload)) return
	const views = state[payload.module].views[payload.query_type]
	if (!views.data) views.data = []
	views.data = [{ name: payload.name, view: payload.view }, ...views.data.filter(item => item.name !== payload.name)]
}

export const UPDATE_REMOVED_DATA_VIEW = 'UPDATE_REMOVED_DATA_VIEW'
export const updateRemovedDataView = (state, payload) => {
	if (!getModule(state, payload)) return

	state[payload.module].views.saved.data =
		state[payload.module].views.saved.data.filter(query => !payload.ids.includes(query.uuid))
}

export const UPDATE_DATA_FIELDS = 'UPDATE_DATA_FIELDS'
export const updateDataFields = (state, payload) => {
	if (!getModule(state, payload)) return
	const fields = state[payload.module].fields
	fields.fetching = payload.fetching
	fields.error = payload.error
	if (payload.data) {
		fields.data = { generic: payload.data.generic, specific: {}, schema: payload.data.schema}
		Object.keys(payload.data.specific).forEach((name) => {
			fields.data.specific[name] = payload.data.specific[name]
			fields.data.generic[0].items.enum.push({name, title: pluginMeta[name].title})
		})
		fields.data.generic[0].items.enum.sort((first, second) => (first.title < second.title) ? -1 : 1)
	}
}


export const UPDATE_DATA_LABELS = 'UPDATE_DATA_LABELS'
export const updateDataLabels = (state, payload) => {
	if (!getModule(state, payload)) return
	const labels = state[payload.module].labels
	labels.fetching = payload.fetching
	labels.error = payload.error
	if (payload.data) {
		labels.data = payload.data.map((label) => {
			return { name: label, title: label}
		})
	}
}

const isEntitySelected = (id, entities) => {
	return (entities.include && entities.ids.includes(id)) || (!entities.include && !entities.ids.includes(id))
}

export const UPDATE_ADDED_DATA_LABELS = 'UPDATE_ADDED_DATA_LABELS'
export const updateAddedDataLabels = (state, payload) => {
	if (!getModule(state, payload)) return
	let data = payload.data
	state[payload.module].labels.data = state[payload.module].labels.data
		.filter(label => !data.labels.includes(label.name))
		.concat(data.labels.map((label) => {
			return {name: label, title: label}
		}))

	let content = [...state[payload.module].content.data]
	content.forEach(function (entity) {
		if (!isEntitySelected(entity.internal_axon_id, data.entities)) return
		if (!entity.labels) entity.labels = []

		entity.labels = Array.from(new Set([ ...entity.labels, ...data.labels ]))
	})
	state[payload.module].content.data = content

	let current = state[payload.module].current.data
	if (current && current.internal_axon_id && isEntitySelected(current.internal_axon_id, data.entities)) {
		state[payload.module].current.data = { ...current,
			labels: Array.from(new Set([ ...current.labels, ...data.labels]))
		}
	}
}

export const UPDATE_REMOVED_DATA_LABELS = 'UPDATE_REMOVED_DATA_LABELS'
export const updateRemovedDataLabels = (state, payload) => {
	if (!getModule(state, payload)) return
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
		if (!isEntitySelected(entity.internal_axon_id, data.entities)) return
		if (!entity.labels) { return }
		entity.labels = entity.labels.filter((label) => !data.labels.includes(label))
	})
	state[payload.module].content.data = content

	let current = state[payload.module].current.data
	if (current && current.internal_axon_id && isEntitySelected(current.internal_axon_id, data.entities) && current.labels) {
		state[payload.module].current.data = { ...current,
			labels: current.labels.filter((label) => !data.labels.includes(label))
		}
	}
}

export const UPDATE_DATA_BY_ID = 'UPDATE_DATA_BY_ID'
export const updateDataByID = (state, payload) => {
	if (!getModule(state, payload)) return
	const current = state[payload.module].current
	current.fetching = payload.fetching
	current.error = payload.error
	if (payload.data) {
		current.data = payload.data
	}
}

export const UPDATE_SAVED_DATA_NOTE = 'UPDATE_SAVED_DATA_NOTE'
export const updateSavedDataNote = (state, payload) => {
    let module = getModule(state, payload)
    if (!payload.fetching && !payload.error) {
        let notes = module.current.data.generic.data.find(item => item.name === 'Notes')
        if (payload.noteId) {
            notes.data = notes.data.map((item) => {
                if (item.uuid === payload.noteId) {
                    return { ...item, ...payload.data }
                }
                return item
            })
        } else {
			if (!notes) {
				notes = {
					name: 'Notes', data: []
				}
				module.current.data.generic.data.push(notes)
			}
            notes.data.push(payload.data)
        }
    }
}

export const UPDATE_REMOVED_DATA_NOTE = 'UPDATE_REMOVED_DATA_NOTE'
export const updateRemovedDataNote = (state, payload) => {
    let module = getModule(state, payload)
    if (!payload.fetching && !payload.error) {
        let notes = module.current.data.generic.data.find(item => item.name === 'Notes')
        notes.data = notes.data.filter(note => !payload.noteIdList.includes(note.uuid))
    }
}

export const UPDATE_SYSTEM_CONFIG = 'UPDATE_SYSTEM_CONFIG'
export const updateSystemConfig = (state, payload) => {
	state.configuration.fetching = payload.fetching
	state.configuration.error = payload.error
	if (payload.data) {
		state.configuration.data = {...state.configuration.data, ...payload.data}
	}
}