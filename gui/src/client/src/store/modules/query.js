import { REQUEST_API } from '../actions'

export const SAVE_QUERY = 'SAVE_QUERY'
export const ADD_QUERY = 'ADD_QUERY'

export const query = {
    state: {
        retrievedQueries: { fetching: false, data: [], error: ''}
    },
    getters: {

    },
    mutations: {
        [ADD_QUERY] (state, payload) {
            state.retrivedQueries.data.push(payload)
        }
    },
    actions: {
        [ SAVE_QUERY ] ({ dispatch, commit }, payload) {
            if (!payload.query) { return }
            if (!payload.name) { payload.name = payload.query }
            dispatch(REQUEST_API, {
                rule: 'api/filters',
                method: 'POST',
                data: payload
            }).then((response) => {
                if (response !== "") {
                    return
                }
                commit(ADD_QUERY, payload)
            }).catch(() => {

            })
        }
    }
}