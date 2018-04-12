import {REQUEST_API} from "../actions";

export const DISABLE_USERS = 'DISABLE_USERS'


export const user = {
    state: {
        data: {
            content: {data: [], fetching: false, error: ''},
            count: {data: 0, fetching: false, error: ''},
            view: {
                page: 0, pageSize: 20, fields: [
                    'specific_data.data.image', 'specific_data.data.username', 'specific_data.data.domain',
                    'specific_data.data.last_seen', 'specific_data.data.is_admin',
                ], coloumnSizes: [], query: {filter: '', expressions: []}, sort: {field: '', desc: true}
            },
            views: {data: [], fetching: false, error: ''},
            fields: {data: [], fetching: false, error: ''},
            queries: {
                saved: {data: [], fetching: false, error: ''},
                history: {data: [], fetching: false, error: ''}
            }
        }
    },
    actions: {
        [DISABLE_USERS]({dispatch, commit}, payload) {
            if (!payload) {
                return
            }
            return dispatch(REQUEST_API, {
                rule: `user/disable`,
                method: 'POST',
                data: payload
            })
        },
    }
}