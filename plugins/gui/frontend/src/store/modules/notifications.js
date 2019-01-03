import { REQUEST_API } from '../actions'

export const FETCH_AGGREGATE_NOTIFICATIONS = 'FETCH_NOTIFICATIONS'
export const UPDATE_AGGREGATE_NOTIFICATIONS = 'UPDATE_AGGREGATE_NOTIFICATIONS'
export const FETCH_NOTIFICATION = 'FETCH_NOTIFICATION'
export const SET_NOTIFICATION = 'SET_NOTIFICATION'
export const UPDATE_NOTIFICATIONS_SEEN = 'UPDATE_NOTIFICATIONS_SEEN'
export const SAVE_NOTIFICATIONS_SEEN = 'SAVE_NOTIFICATIONS_SEEN'
export const FETCH_NOTIFICATIONS_UNSEEN_COUNT = 'FETCH_NOTIFICATIONS_UNSEEN_COUNT'
export const SET_NOTIFICATIONS_UNSEEN_COUNT = 'SET_NOTIFICATIONS_UNSEEN_COUNT'


export const notifications = {
	state: {
		/* Notifications DataTable State */
		content: { data: [], fetching: false, error: ''},
		count: { data: 0, fetching: false, error: ''},
		view: {
			page: 0, pageSize: 20, fields: [
				'severity', 'date_fetched', 'plugin_name', 'title'
			], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
		},
		fields: { data: { generic: [
			{ name: 'uuid' },
			{ name: 'severity', title: 'Severity', type: 'string', format: 'icon' },
			{ name: 'date_fetched', title: 'Date Time', type: 'string', format: 'date-time' },
			{ name: 'plugin_name', title: 'Source', type: 'string' },
			{ name: 'title', title: 'Title', type: 'string' },
			{ name: 'seen' }
		]}},


		aggregatedList: { fetching: false, data: [], error: '' },

		/* A single fetched notifications, according to user selection */
		current: { fetching: false, data: { seen: false }, error: '' },

		unseenCount: { fetching: false, data: 0, error: ''},

	},
	mutations: {
		[ UPDATE_AGGREGATE_NOTIFICATIONS ] (state, payload) {
			state.aggregatedList.fetching = payload.fetching
			state.aggregatedList.error = payload.error
			if (payload.data) {
				state.aggregatedList.data = payload.data.slice(0, 6)
			}
		},
		[ SET_NOTIFICATION ] (state, payload) {
			state.current.fetching = payload.fetching
			state.current.error = payload.error
			if (payload.data) {
				state.current.data = { ...payload.data }
			}
		},
		[ SAVE_NOTIFICATIONS_SEEN ] (state, {ids}) {
			state.content.data = [ ...state.content.data ]
			state.content.data.forEach((notification) => {
				if (ids.length === 0 || ids.indexOf(notification.uuid) > -1) {
					notification.seen = true
                    state.unseenCount.data--
				}
			})
			if (ids.length === 0) state.unseenCount.data = 0
		},
        [ SET_NOTIFICATIONS_UNSEEN_COUNT ] (state, payload) {
            state.unseenCount.fetching = payload.fetching
            state.unseenCount.error = payload.error
            if (payload.data) {
                state.unseenCount.data = payload.data
            }
        }
	},
	actions: {
		[ FETCH_AGGREGATE_NOTIFICATIONS ] ({dispatch}) {
			/*
				Get notifications belonging to the page defined by payload.skip and payload.limit
				If skip is 0 or not given, it is interpreted as first page and entire list is restarted
				If limit is not given, returned amount is still limited by PAGINATION_LIMIT_MAX defined in backend
			 */
			return dispatch(REQUEST_API, {
				rule: 'notifications?aggregate=true',
				type: UPDATE_AGGREGATE_NOTIFICATIONS
			})
		},
		[ FETCH_NOTIFICATION ] ({dispatch}, notificationId) {
			if (!notificationId) { return }
			dispatch(REQUEST_API, {
				rule: `notifications/${notificationId}`,
				type: SET_NOTIFICATION
			})
		},
		[ UPDATE_NOTIFICATIONS_SEEN ] ({dispatch}, notificationIds) {
			/*
				Mark given notifications as seen by user
			 */
			if (!notificationIds) { return }
			dispatch(REQUEST_API, {
				rule: 'notifications',
				method: 'POST',
                type: SAVE_NOTIFICATIONS_SEEN,
				data: { 'notification_ids': notificationIds },
                payload: {
                    ids: notificationIds
                }
			})
		},
        [ FETCH_NOTIFICATIONS_UNSEEN_COUNT ] ({dispatch}, payload) {
            /*
                Request the number of unseen notifications, matching a filter, if given
             */
            if (!payload.filter) {
                payload.filter = "seen == false"
            } else {
                payload.filter = `(${payload.filter}) and seen == false`
            }
            let rule = `notifications/count?filter=${payload.filter}`
            return dispatch(REQUEST_API, {
                rule: rule,
                type: SET_NOTIFICATIONS_UNSEEN_COUNT
            })
        },
	}
}