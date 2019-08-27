import { getModule } from './actions'
import { pluginMeta } from '../constants/plugin_meta'
import { initCustomData } from '../constants/entities'

export const TOGGLE_SIDEBAR = 'TOGGLE_SIDEBAR'
export const toggleSidebar = (state) => {
    state.interaction.collapseSidebar = !state.interaction.collapseSidebar
}

export const UPDATE_DATA = 'UPDATE_DATA'
export const updateData = (state, payload) => {
	let moduleState = getModule(state, payload)
	moduleState.fetching = payload.fetching
	moduleState.error = payload.error
	if (payload.data) {
		moduleState.data = payload.data
	}
}

export const UPDATE_WINDOW_WIDTH = 'UPDATE_WINDOW_WIDTH'
export const updateWindowWidth = (state) => {
	state.interaction.windowWidth = document.documentElement.clientWidth
}

export const UPDATE_LANGUAGE = 'UPDATE_LANGUAGE'
export const updateLanguage = (state, payload) => {
	state.interaction.language = payload
}

export const UPDATE_BRANCH = 'UPDATE_BRANCH'
export const updateBranch = (state, payload) => {
	state.interaction.branch = payload
}

function clearUrlFromQuick(url) {
	return url.replace('&quick=True', '').replace('&quick=False', '').
	replace('quick=True', '').replace('quick=False', '')
}
export const UPDATE_DATA_COUNT_QUICK = 'UPDATE_DATA_COUNT_QUICK'
export const updateDataCountQuick = (state, payload) => {
	let module = getModule(state, payload)
	if (!module) return
	const count = module.count
	if (!payload.fetching && count.rule !== clearUrlFromQuick(payload.rule)) {
		return
	}

	count.fetching = payload.fetching
	count.error = payload.error
	count.rule = clearUrlFromQuick(payload.rule)

	if (payload.data !== undefined) {
		if (count.data == undefined) {
			count.data = payload.data
			count.data_to_show = payload.data
			if (payload.data == '1000') {
				count.data_to_show = '> 1000, loading...'
			}
		}
	}
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
		count.data_to_show = payload.data
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
export const updateDataView = (state, payload) => {UPDATE_DATA_VIEW
	let module = getModule(state, payload)
	if (!module) return
	if (payload.view) {
		if (module.view.query && payload.view.query && module.view.query.filter !== payload.view.query.filter
			|| (payload.view.historical !== undefined && module.view.historical !== payload.view.historical)) {
			module.content.data = []
			module.count.data_to_show = 0
		}
		module.view = { ...module.view, ...payload.view }
	}
	if (payload.uuid !== undefined) {
		state[payload.module] = { ...module, selectedView: payload.uuid }
	}
	if (payload.name !== undefined) {
		let matchingView = module.views.saved.content.data.find(view => view.name === payload.name)
		state[payload.module] = {
			...module,
			selectedView: matchingView? matchingView.uuid : null
		}
	}
}

export const UPDATE_DATA_VIEW_FILTER = 'UPDATE_DATA_VIEW_FILTER'
export const updateDataViewFilter = (state, payload) => {UPDATE_DATA_VIEW_FILTER
	let module = getModule(state, payload)
	if (!module) return
	if (payload.view) {
		module.view.colFilters = payload.view.colFilters
	}
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
	const views = state[payload.module].views.saved.content
	if (!views.data) views.data = []
	views.data = [{
		uuid: payload.uuid, name: payload.name, view: payload.view
	}, ...views.data.filter(item => item.name !== payload.name)]
}

export const CHANGE_DATA_VIEW = 'CHANGE_DATA_VIEW'
export const changeDataView = (state, payload) => {
	let stateModule = getModule(state, payload)
	if (!stateModule) return
	const views = stateModule.views.saved.content
	if (!views || !views.data || !views.data.length) return
	views.data = views.data.map(item => {
		if (item.uuid === payload.uuid) {
			item.name = payload.name
			item.view = payload.view
		}
		return item
	})
}

export const UPDATE_REMOVED_DATA_VIEW = 'UPDATE_REMOVED_DATA_VIEW'
export const updateRemovedDataView = (state, payload) => {
	if (!getModule(state, payload)) return

	state[payload.module].content.data =
		state[payload.module].content.data.filter(query => !payload.selection.includes(query.uuid))
}

export const UPDATE_DATA_FIELDS = 'UPDATE_DATA_FIELDS'
export const updateDataFields = (state, payload) => {
	if (!getModule(state, payload)) return
	const fields = state[payload.module].fields
	fields.fetching = payload.fetching
	fields.error = payload.error
	if (payload.data) {
		fields.data = { generic: payload.data.generic, specific: {}, schema: payload.data.schema }
		Object.keys(payload.data.specific).forEach((name) => {
			let pluginMetadata = pluginMeta[name]
			if (!pluginMetadata)
				return
			fields.data.specific[name] = payload.data.specific[name]
			fields.data.generic[0].items.enum.push({name, title: pluginMetadata.title || name})
		})
		fields.data.generic[0].items.enum.sort((first, second) => (first.title < second.title) ? -1 : 1)
	}
}

export const UPDATE_DATA_HYPERLINKS = 'UPDATE_DATA_HYPERLINKS'
export const updateDataHyperlinks = (state, payload) => {
	if (!getModule(state, payload)) return
	const fields = state[payload.module].hyperlinks
	fields.fetching = payload.fetching
	fields.error = payload.error
	if (payload.data) {
		fields.data = payload.data
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
	let module = getModule(state, payload)
	let data = payload.data
	module.labels.data = module.labels.data
		.filter(label => !data.labels.includes(label.name))
		.concat(data.labels.map((label) => {
			return {name: label, title: label}
		}))

	module.content.data = module.content.data.map(entity => {
		if (!isEntitySelected(entity.internal_axon_id, data.entities)) return entity
		if (!entity.labels) entity.labels = []

		return {
			...entity, labels: Array.from(new Set([ ...entity.labels, ...data.labels ]))
		}
	})

	let currentData = module.current.data
	if (module.current.id && isEntitySelected(module.current.id, data.entities)) {
		module.current.data = { ...currentData,
			labels: Array.from(new Set([ ...currentData.labels, ...data.labels]))
		}
	}
}

export const UPDATE_REMOVED_DATA_LABELS = 'UPDATE_REMOVED_DATA_LABELS'
export const updateRemovedDataLabels = (state, payload) => {
	let module = getModule(state, payload)
	let data = payload.data
	module.labels.data = module.labels.data.filter((label) => {
		if (!data.labels.includes(label.name)) return true
		return module.content.data.reduce((exists, entity) => {
			return exists || (!entity.labels || entity.labels.includes(label.name))
		}, false)
	})

	module.content.data = module.content.data.map(entity => {
		if (!isEntitySelected(entity.internal_axon_id, data.entities) || !entity.labels) return entity

		return {
			...entity, labels: entity.labels.filter((label) => !data.labels.includes(label))
		}
	})

	let currentData = module.current.data
	if (module.current.id && isEntitySelected(module.current.id, data.entities) && currentData.labels) {
		module.current.data = { ...currentData,
			labels: currentData.labels.filter((label) => !data.labels.includes(label))
		}
	}
}

export const SELECT_DATA_CURRENT = 'SELECT_DATA_CURRENT'
export const selectDataCurrent = (state, payload) => {
	let module = getModule(state, payload)
	module.current.id = payload.id
	if (!payload.id) {
		module.current.data = {}
		module.current.tasks.data = []
	}
}

export const UPDATE_DATA_CURRENT = 'UPDATE_DATA_CURRENT'
export const updateDataCurrent = (state, payload) => {
	let moduleState = getModule(state, payload)
	moduleState.fetching = payload.fetching
	moduleState.error = payload.error
	if (payload.data) {
		moduleState.data = { ...payload.data,
      advanced: payload.data.advanced.map(item => {
        return {
          data: item.data,
          view: {
            page: 0, pageSize: 20,
            coloumnSizes: [], query: {
              filter: '', expressions: [], search: ''
            }, sort: {
              field: '', desc: true
            },
            historical: null
          },
          schema: item.schema
        }
      }, {})
    }
	}
}

export const UPDATE_SAVED_DATA_NOTE = 'UPDATE_SAVED_DATA_NOTE'
export const updateSavedDataNote = (state, payload) => {
	let module = getModule(state, payload)
	if (!payload.fetching && !payload.error) {
		let notes = module.current.data.data.find(item => item.name === 'Notes')
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
				module.current.data.data.push(notes)
			}
			notes.data.push(payload.data)
		}
	}
}

export const UPDATE_REMOVED_DATA_NOTE = 'UPDATE_REMOVED_DATA_NOTE'
export const updateRemovedDataNote = (state, payload) => {
    let module = getModule(state, payload)
    if (!payload.fetching && !payload.error) {
        let notes = module.current.data.data.find(item => item.name === 'Notes')
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

export const UPDATE_SYSTEM_EXPIRED = 'UPDATE_SYSTEM_EXPIRED'
export const updateSystemExpired = (state, payload) => {
	state.expired.fetching = payload.fetching
	state.expired.error = payload.error
	if (payload.data !== undefined) {
		state.expired.data = payload.data
	}
}

export const UPDATE_CUSTOM_DATA = 'UPDATE_CUSTOM_DATA'
export const updateCustomData = (state, payload) => {
	let module = getModule(state, payload)
	if (!payload.fetching || !module.current.data.adapters) return
	let guiAdapter = module.current.data.adapters.find(item => item.name === 'gui')
	let data = payload.data.reduce((map, field) => {
		let canonizedName = field.name.split(' ').join('_').toLowerCase()
		if (!field.predefined) {
			canonizedName = `custom_${canonizedName}`
		}
		map[canonizedName] = field.value
		return map
	}, {})
	if (guiAdapter) {
		guiAdapter.data = data
	} else {
		module.current.data.adapters.push({
			...initCustomData(payload.module),
			data
		})
	}
}

export const SHOW_TOASTER_MESSAGE = 'SHOW_TOASTER_MESSAGE'
export const showToasterMessage = ( state, { message, timeout }) => {
	state.toast.message = message
	if(timeout !== undefined) {
		state.toast.timeout = timeout
	}
}

export const REMOVE_TOASTER = 'REMOVE_TOASTER'
export const removeToaster = (state) => {
	state.toast.message = ''
}