import { REQUEST_API } from '../actions';

export const SET_LABELS = 'SET_LABELS';
export const LAZY_FETCH_LABELS = 'LAZY_FETCH_LABELS';
export const GET_LABELS = 'GET_LABELS';
export const GET_LABELS_BY_MODULE = 'GET_LABELS_BY_MODULE';

import _isEmpty from 'lodash/isEmpty';

export const labels = {
  state: {
    labels: null,
  },
  getters: {
    [GET_LABELS]: (state) => state.labels,
    [GET_LABELS_BY_MODULE]: (state) => (module) => (state.labels ? state.labels[module] : {}),
  },
  mutations: {
    [SET_LABELS](state, payload) {
      if (payload.data) {
        state.labels = payload.data;
      }
    },
  },
  actions: {
    [LAZY_FETCH_LABELS]({ state, dispatch }) {
      /*
          Call API to save labels
       */
      if (!_isEmpty(state.labels)) {
        return Promise.resolve();
      }
      const rule = 'labels';
      return dispatch(REQUEST_API, {
        rule,
        type: SET_LABELS,
      });
    },
  },
};
