import Promise from 'promise'
import { REQUEST_API, FETCH_DATA_CONTENT } from '../actions'

export const FETCH_ENFORCEMENT = 'FETCH_ENFORCEMENT'
export const SET_ENFORCEMENT = 'SET_ENFORCEMENT'
export const SAVE_ENFORCEMENT = 'SAVE_ENFORCEMENT'
export const FETCH_SAVED_ENFORCEMENTS = 'FETCH_SAVED_ENFORCEMENTS'
export const UPDATE_SAVED_ENFORCEMENTS = 'UPDATE_SAVED_ENFORCEMENTS'
export const REMOVE_ENFORCEMENTS = 'REMOVE_ENFORCEMENTS'
export const RUN_ENFORCEMENT = 'RUN_ENFORCEMENT'
export const FETCH_ACTIONS = 'FETCH_ACTIONS'
export const UPDATE_ACTIONS = 'UPDATE_ACTIONS'
export const FETCH_SAVED_ACTIONS = 'FETCH_SAVED_ACTIONS'
export const UPDATE_SAVED_ACTIONS = 'UPDATE_SAVED_ACTIONS'

export const initAction = {
  name: '',
  action: {
    action_name: '',
    config: null
  }
}

export const initRecipe = {
  main: null,
  success: [],
  failure: [],
  post: []
}

export const initTrigger = {
  view: {
    name: '',
    entity: ''
  },
  run_on: 'AllEntities',
  period: 'never',
  conditions: {
    new_entities: false,
    previous_entities: false,
    above: null,
    below: null
  }
}

export const enforcements = {
  state: {
    /* Enforcements DataTable State */

    content: { data: [], fetching: false, error: '' },

    count: { data: 0, fetching: false, error: '' },

    view: {
      page: 0, pageSize: 20, coloumnSizes: [], query: {
        filter: '', expressions: []
      }, sort: {
        field: '', desc: true
      }
    },

    savedEnforcements: { fetching: false, data: [], error: '' },

    /* Data of Enforcement currently being configured */
    current: { fetching: false, data: {}, error: '' },

    actions: { fetching: false, data: {}, error: '' },

    savedActions: { fetching: false, data: [], error: '' }

  },
  mutations: {
    [SET_ENFORCEMENT] (state, enforcementData) {
      /*
          Set given data, if given, or a new Enforcement otherwise, as Enforcement in the handle
       */
      if (enforcementData) {
        state.current.data = { ...enforcementData }
      } else {
        state.current.data = {
          actions: {
            main: null,
            success: [],
            failure: [],
            post: []
          },
          triggers: []
        }
      }
    },
    [UPDATE_ACTIONS] (state, payload) {
      state.actions.fetching = payload.fetching
      state.actions.error = payload.error
      if (payload.data) {
        state.actions.data = payload.data
      }
    },
    [UPDATE_SAVED_ENFORCEMENTS] (state, payload) {
      state.savedEnforcements.fetching = payload.fetching
      state.savedEnforcements.error = payload.error
      if (payload.data) {
        state.savedEnforcements.data = payload.data
      }
    },
    [UPDATE_SAVED_ACTIONS] (state, payload) {
      state.savedActions.fetching = payload.fetching
      state.savedActions.error = payload.error
      if (payload.data) {
        state.savedActions.data = payload.data
      }
    }
  },
  actions: {
    [FETCH_ENFORCEMENT] ({ dispatch, commit }, enforcementId) {
      /*
          Ask server for a complete, specific enforcement, if given an actual ID.
          Set the response as the enforcement in handling.
          Otherwise, initialize a new enforcement to handle.
       */
      if (!enforcementId || enforcementId === 'new') {
        return new Promise((resolve) => {
          commit(SET_ENFORCEMENT)
          resolve()
        })
      }

      return dispatch(REQUEST_API, {
        rule: `enforcements/${enforcementId}`
      }).then((response) => {
        if (response.status === 200 && response.data) {
          commit(SET_ENFORCEMENT, response.data)
        } else {
          commit(SET_ENFORCEMENT)
        }
      })
    },
    [SAVE_ENFORCEMENT] ({ dispatch }, enforcement) {
      /*
          Update an existing Enforcement, if given an id, or create a new one otherwise
       */
      let handleSuccess = (id) => {
        dispatch(FETCH_DATA_CONTENT, { module: 'enforcements', skip: 0 })
        dispatch(FETCH_DATA_CONTENT, { module: 'tasks', skip: 0 })
        dispatch(FETCH_ENFORCEMENT, id)
      }

      if (enforcement.uuid && enforcement.uuid !== 'new') {
        return dispatch(REQUEST_API, {
          rule: `enforcements/${enforcement.uuid}`,
          method: 'POST',
          data: enforcement
        }).then((response) => {
          if (response.status === 200) {
            return handleSuccess(enforcement.uuid)
          }
        })
      } else {
        return dispatch(REQUEST_API, {
          rule: 'enforcements',
          method: 'PUT',
          data: enforcement
        }).then((response) => {
          if (response.status === 201 && response.data) {
            handleSuccess(response.data)
            return response.data
          }
        })
      }
    },
    [REMOVE_ENFORCEMENTS] ({ dispatch }, selection) {
      /*
          Remove given selection of Enforcement.
          Expected structure is a list of ids and a flag indicating whether to include or exclude them
       */
      return dispatch(REQUEST_API, {
        rule: 'enforcements',
        method: 'DELETE',
        data: selection
      }).then((response) => {
        if (response.status === 200) {
          dispatch(FETCH_DATA_CONTENT, { module: 'enforcements', skip: 0 })
        }
      })
    },
    [FETCH_SAVED_ENFORCEMENTS] ({ dispatch }) {
      return dispatch(REQUEST_API, {
        rule: 'enforcements/saved',
        type: UPDATE_SAVED_ENFORCEMENTS
      })
    },
    [FETCH_ACTIONS] ({ dispatch }) {
      /*
          Get list of actions and each one's schema
       */
      return dispatch(REQUEST_API, {
        rule: 'enforcements/actions',
        type: UPDATE_ACTIONS
      })
    },
    [FETCH_SAVED_ACTIONS] ({ dispatch }) {
      return dispatch(REQUEST_API, {
        rule: 'enforcements/actions/saved',
        type: UPDATE_SAVED_ACTIONS
      })
    },
    [RUN_ENFORCEMENT] ({ dispatch }, enforcementId) {
      return dispatch(REQUEST_API, {
        rule: `enforcements/${enforcementId}/trigger`,
        method: 'POST'
      })
    }
  }
}