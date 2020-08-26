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
      queryStrings: {
        date_from: null,
        date_to: null,
      },
    },
  },
  actions: {
    [FETCH_CSV]({ dispatch, state }) {
      const params = [];
      const search = _get(state, 'view.query.search', '');
      if (search) {
        params.push(`search=${search}`);
      }
      const queryStrings = _get(state, 'view.queryStrings', {});
      Object.keys(queryStrings)
        .filter((item) => queryStrings[item])
        .forEach((key) => {
          params.push(`${key}=${queryStrings[key]}`);
        });

      return dispatch(REQUEST_API, {
        rule: `settings/audit/csv?${params.join('&')}`,
      }).then((response) => downloadFile('csv', response));
    },
  },
};
