import { REQUEST_API } from '../actions';

export const SET_LABELS = 'SET_LABELS';
export const FETCH_LABELS = 'FETCH_LABELS';
export const GET_LABELS = 'GET_LABELS';
export const GET_LABELS_BY_MODULE = 'GET_LABELS_BY_MODULE';

export const labels = {
  state: {
    labels: null,
  },
  getters: {
    [GET_LABELS]: (state) => state.labels,
    [GET_LABELS_BY_MODULE]: (state) => (module) => state.labels ? state.labels[module] : {},
  },
  mutations: {
    [SET_LABELS](state, payload) {
      if (payload.data) {
        state.labels = payload.data;
      }
    },
  },
  actions: {
    [FETCH_LABELS]({ dispatch }) {
      /*
          Call API to save labels
       */

      const rule = 'labels';
      return dispatch(REQUEST_API, {
        rule,
        type: SET_LABELS,
      });
    },
  },
};
