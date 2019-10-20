import _get from 'lodash/get'
import { REQUEST_API } from '../actions'

export const UPDATE_EMPTY_STATE = 'UPDATE_EMPTY_STATE'

// Getting Strated constants - I used namspaces so it would be easier to inspect in the console (this is just a proposal):
// Note: this is not the same as namspacing in the spec.

// featch data from server
export const GET_GETTING_STARTED_DATA = 'onboarding/gettingStarted/data/fetch'
// insert http result into store
export const SET_GETTING_STARTED_DATA = 'onboarindg/gettingStarted/data/set'
// update settings
export const UPDATE_GETTING_STARTED_SETTINGS = 'onboarding/gettingStarted/data/settings/update'
// update milestone completed
export const SET_GETTING_STARTED_MILESTONE_COMPLETION = 'onboarding/gettingStarted/data/milestones/completionEvent'

const completeMilestoneStatusByName = milestoneName => milestone => {
	if (milestone.name === milestoneName) {
		return {
			...milestone,
			completed: true,
			completionDate: Date.now()
		}
	}
	return milestone
}
export const onboarding = {
	/*
	This module is responsible for walking users through the capabilities of the system.
		1. Empty states - when users 'land' on a feature they never used before or try to do something that depends on
		   another operation they never performed.
		2. Getting Started With Axonius - as part of our self-served strategy, the Getting Started checklist will guied users how to
		   achvie milestones and get the most out of our platform.
	 */
	state: {
		emptyStates: {
			settings: {
				mail: false,
				syslog: false,
				httpsLog: false,
				jira: false
			}
		},
		gettingStarted: {
			loading: false,
			error: false,
			data: {
				milestones: [],
				settings: {}
			}
		}
	},
	mutations: {
		[ UPDATE_EMPTY_STATE ] (state, payload) {
			state.emptyStates.settings = { ...state.emptyStates.settings, ...payload.settings }
		},

		[ SET_GETTING_STARTED_DATA ] (state, payload) {
			const { data, error, fetching } = payload
			state.gettingStarted.loading = fetching
			if (data) {
				state.gettingStarted.data = data[0]
			}
			if (error) {
				state.gettingStarted.error = error
			} 
		},

		[ UPDATE_GETTING_STARTED_SETTINGS ] (state, payload) {
			const settings = _get(state, 'gettingStarted.data.settings', {})
			state.gettingStarted.data.settings = {...settings, payload}
		},
	},
	actions: {
		async [ GET_GETTING_STARTED_DATA ] ({ commit, dispatch }) {
			try {
				await dispatch(REQUEST_API, {
					rule: `getting_started`,
					type: SET_GETTING_STARTED_DATA
				})
			} catch(error) {
				console.error(error)
			}
		},
		async [ SET_GETTING_STARTED_MILESTONE_COMPLETION ] ({ state, dispatch, commit, getters }, payload) {
			try {
				// Dont execute the action in case the milestone has already been completed
				const { completedMilestonesNames } = getters
				if (completedMilestonesNames.includes(payload.milestoneName)) {
					return
				}
				const history = state.gettingStarted.data.milestones
				const updateMilestoneCompletion = completeMilestoneStatusByName(payload.milestoneName)
				
				const updatedMilestonesdata = history.map(updateMilestoneCompletion)
				commit(SET_GETTING_STARTED_DATA, updatedMilestonesdata)

				await dispatch(REQUEST_API, {
					rule: `getting_started/completion`,
					method: 'POST',
					data: {milestoneName: payload.milestoneName}
				})
			}catch(err) {
				console.error(err)
				// revert to previous state incase the operation failed for some reason
				commit(SET_GETTING_STARTED_DATA, history)
			}
		},

		async [ UPDATE_GETTING_STARTED_SETTINGS ] ({ commit, dispatch, state }, payload) {

			const history = state.gettingStarted.data.settings

			try {
				await dispatch(REQUEST_API, {
					rule: 'getting_started/settings',
					data: {settings: payload},
					method: 'POST'
				})
				commit(UPDATE_GETTING_STARTED_SETTINGS, payload)
			} catch (error) {
				// revert to previous state incase the operation failed for some reason
				commit(UPDATE_GETTING_STARTED_SETTINGS, history)
				console.error(error)
			}
		}
	},
	getters: {
		completedMilestones: state => {
			const data = _get(state, 'gettingStarted.data.milestones', [])
			return data.filter(m => m.completed)
		},
		completedMilestonesNames: (state, getters) => {
			return getters.completedMilestones.map(m => m.name)
		}
	}
}
