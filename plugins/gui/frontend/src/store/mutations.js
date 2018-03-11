
export const TOGGLE_SIDEBAR = 'TOGGLE_SIDEBAR'
export const toggleSidebar = (state) => {
    state.interaction.collapseSidebar = !state.interaction.collapseSidebar
}


export const UPDATE_TABLE_COUNT = 'UPDATE_TABLE_COUNT'
export const updateTableCount = (state, payload) => {
	if (!payload.module || !state[payload.module] || !state[payload.module].dataTable) return
	const count = state[payload.module].dataTable.count
	count.fetching = payload.fetching
	count.error = payload.error
	if (payload.data !== undefined) {
		count.data = payload.data
	}
}

export const UPDATE_TABLE_CONTENT = 'UPDATE_TABLE_CONTENT'
export const updateTableContent = (state, payload) => {
	if (!payload.module || !state[payload.module] || !state[payload.module].dataTable) return
	const content = state[payload.module].dataTable.content
	content.fetching = payload.fetching
	content.error = payload.error
	if (payload.data) {
		content.data = payload.restart? []: [ ...content.data ]
		payload.data.forEach((device) => {
			content.data.push({ ...device })
		})
	}
}

export const UPDATE_TABLE_VIEW = 'UPDATE_TABLE_VIEW'
export const updateTableView = (state, payload) => {
	if (!payload.module || !state[payload.module] || !state[payload.module].dataTable) return
	let table = state[payload.module].dataTable
	if (payload.view.filter || payload.view.sort) {
		table.content.data = []
		table.count.data = 0
	}
	table.view = { ...state[payload.module].dataTable.view, ...payload.view }
}

export const UPDATE_TABLE_VIEWS = 'UPDATE_TABLE_VIEWS'
export const updateTableViews = (state, payload) => {
	if (!payload.module || !state[payload.module] || !state[payload.module].dataViews) return
	const views = state[payload.module].dataViews
	views.fetching = payload.fetching
	views.error = payload.error
	if (payload.data) {
		views.data = [ ]
		payload.data.forEach((view) => views.data.push({ ...view }))
	}
}

export const ADD_TABLE_VIEW = 'ADD_TABLE_VIEW'
export const addTableView = (state, payload) => {
	if (!payload.module || !state[payload.module] || !state[payload.module].dataViews) return
	const views = state[payload.module].dataViews
	if (!views.data) views.data = []
	views.data = [{ name: payload.name, view: payload.view }, ...views.data]
}

