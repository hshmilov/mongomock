import { downloadFile, REQUEST_API } from '@store/actions';
import _get from 'lodash/get';

export const FETCH_CSV = 'FETCH_CSV';

export default {
  state: {
    content: {
      data: [], fetching: false, error: '', rule: '',
    },

    count: {
      data: 0, fetching: false, error: ''
    },

    view: {
      page: 0,
      pageSize: 20,
      fields: [],
      coloumnSizes: [],
      query: {
        filter: '',
        expressions: [],
        search: '',
      },
      colFilters: {},
      historical: null,
    },
  },
  actions: {
    [FETCH_CSV]({ dispatch, state }) {
      const search = _get(state, 'view.query.search', '');
      return dispatch(REQUEST_API, {
        rule: `settings/audit/csv?search=${search}`,
      }).then((response) => downloadFile('csv', response));
    },
  },
};
