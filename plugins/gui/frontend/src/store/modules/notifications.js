import { REQUEST_API } from '../actions'

export const RESTART_NOTIFICATIONS = 'RESTART_NOTIFICATIONS'
export const FETCH_NOTIFICATIONS = 'FETCH_NOTIFICATIONS'
export const UPDATE_NOTIFICATIONS = 'UPDATE_NOTIFICATIONS'
export const FETCH_NOTIFICATION = 'FETCH_NOTIFICATION'
export const SET_NOTIFICATION = 'SET_NOTIFICATION'
export const UPDATE_NOTIFICATIONS_SEEN = 'UPDATE_NOTIFICATIONS_SEEN'
export const SAVE_NOTIFICATIONS_SEEN = 'SAVE_NOTIFICATIONS_SEEN'
export const FETCH_NOTIFICATIONS_UNSEEN = 'FETCH_NOTIFICATIONS_UNSEEN'
export const SET_NOTIFICATIONS_UNSEEN = 'SET_NOTIFICATIONS_UNSEEN'


export const notification = {
	state: {
		/* All fetched notifications */
		notificationList: { fetching: false, data: [], error: '' },

		/* A single fetched notification, according to user selection */
		notificationDetails: { fetching: false, data: { seen: false }, error: '' },

		notificationUnseen: { fetching: false, data: 0, error: ''},

		fields: [
			{ path: 'uuid', hidden: true },
			{ path: 'severity', type: 'status' },
			{ path: 'date_fetched', name: 'Date Time', type: 'timestamp' },
			{ path: 'plugin_name', name: 'Source' },
			{ path: 'title', name: 'Title' },
			{ path: 'seen',  hidden: true }

		]
	},
	mutations: {
		[ RESTART_NOTIFICATIONS ] (state) {
			state.notificationList.data = []
		},
		[ UPDATE_NOTIFICATIONS ] (state, payload) {
			state.notificationList.fetching = payload.fetching
			state.notificationList.error = payload.error
			if (payload.data) {
                if (payload.restart) {
                    state.notificationList.data = [...payload.data]
                }
                else {
                    state.notificationList.data = [...state.notificationList.data, ...payload.data]
				}
			}
		},
		[ SET_NOTIFICATION ] (state, payload) {
			state.notificationDetails.fetching = payload.fetching
			state.notificationDetails.error = payload.error
			if (payload.data) {
				state.notificationDetails.data = { ...payload.data }
			}
		},
		[ SAVE_NOTIFICATIONS_SEEN ] (state, notificationIds) {
			state.notificationList.data = [ ...state.notificationList.data ]
			state.notificationList.data.forEach((notification) => {
				if (notificationIds.indexOf(notification.uuid) > -1) {
					notification.seen = true
				}
			})
			if (!state.notificationUnseen.data || state.notificationUnseen.data < notificationIds.length) return
			state.notificationUnseen.data -= notificationIds.length
		},
		[ SET_NOTIFICATIONS_UNSEEN ] (state, payload) {
			state.notificationUnseen.fetching = payload.fetching
			state.notificationUnseen.error = payload.error
			if (payload.data) {
				state.notificationUnseen.data = payload.data
			}
		}
	},
	actions: {
		[ FETCH_NOTIFICATIONS ] ({dispatch}, payload) {
			/*
				Get notifications belonging to the page defined by payload.skip and payload.limit
				If skip is 0 or not given, it is interpreted as first page and entire list is restarted
				If limit is not given, returned amount is still limited by PAGINATION_LIMIT_MAX defined in backend
			 */
			let params = []
			if (payload && payload.skip) {
				params.push(`skip=${payload.skip}`)
			}
			if (payload && payload.limit) {
				params.push(`limit=${payload.limit}`)
			}
			let rule = 'notifications'
			if (params && params.length) {
				rule += `?${params.join('&')}`
			}
			dispatch(REQUEST_API, {
				rule: rule,
				type: UPDATE_NOTIFICATIONS,
				payload: {restart: !payload || !payload.skip}
			})
		},
		[ FETCH_NOTIFICATION ] ({dispatch}, notificationId) {
			if (!notificationId) { return }
			dispatch(REQUEST_API, {
				rule: `notifications/${notificationId}`,
				type: SET_NOTIFICATION
			})
		},
		[ UPDATE_NOTIFICATIONS_SEEN ] ({dispatch, commit}, notificationIds) {
			/*
				Mark given notifications as seen by user
			 */
			if (!notificationIds || !notificationIds.length) { return }
			dispatch(REQUEST_API, {
				rule: 'notifications',
				method: 'POST',
				data: { 'notification_ids': notificationIds }
			}).then((response) => {
				if (parseInt(response.data) !== notificationIds.length) {
					return
				}
				commit(SAVE_NOTIFICATIONS_SEEN, notificationIds)
			})
		},
		[ FETCH_NOTIFICATIONS_UNSEEN ] ({dispatch}, payload) {
			/*
				Request the number of unseen notifications, matching a filter, if given
			 */
			if (!payload.filter) {
				payload.filter = "seen == false"
			} else {
				payload.filter = `(${payload.filter}) and seen == false`
			}
			let rule = `notifications/count?filter=${payload.filter}`
			dispatch(REQUEST_API, {
				rule: rule,
				type: SET_NOTIFICATIONS_UNSEEN
			})
		}
	}
}