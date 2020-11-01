import Promise from 'promise';
import { REQUEST_API, FETCH_DATA_CONTENT, downloadFile } from '../actions';

export const FETCH_REPORT = 'FETCH_REPORT';
export const SET_REPORT = 'SET_REPORT';
export const SAVE_REPORT = 'SAVE_REPORT';
export const REMOVE_REPORTS = 'REMOVE_REPORTS';
export const RUN_REPORT = 'RUN_REPORT';
export const DOWNLOAD_REPORT = 'DOWNLOAD_REPORT';
export const RESET_REPORTS_STATE = 'RESET_REPORTS_STATE';

const getReportsInitialState = () => ({
  /* Reports DataTable State */
  content: { data: [], fetching: false, error: '' },
  count: { data: 0, fetching: false, error: '' },
  view: {
    page: 0,
    pageSize: 20,
    coloumnSizes: [],
    query: {
      filter: '', expressions: [],
    },
    sort: {
      field: '', desc: true,
    },
  },
});

export const reports = {
  state: {
    ...getReportsInitialState(),
  },
  mutations: {
    [RESET_REPORTS_STATE](state) {
      state = getReportsInitialState();
    },

  },
  actions: {
    [SAVE_REPORT]({ dispatch }, report) {
      /*
        Update the existing reports table and Remove the current report from the store
     */
      const handleSuccess = () => {
        dispatch(FETCH_DATA_CONTENT, { module: 'reports', skip: 0 });
      };

      if (report.uuid && report.uuid !== 'new') {
        return dispatch(REQUEST_API, {
          rule: `reports/${report.uuid}`,
          method: 'POST',
          data: report,
        }).then((response) => {
          if (response.status === 200) {
            return handleSuccess();
          }
        });
      }
      return dispatch(REQUEST_API, {
        rule: 'reports',
        method: 'PUT',
        data: report,
      }).then((response) => {
        if (response.status === 201 && response.data) {
          handleSuccess();
          return response.data;
        }
      });
    },
    [REMOVE_REPORTS]({ dispatch }, selection) {
      /*
        Remove given selection of Report.
        Expected structure is a list of ids and a flag indicating whether to include or exclude them
     */
      return dispatch(REQUEST_API, {
        rule: 'reports',
        method: 'DELETE',
        data: selection,
      }).then((response) => {
        if (response.status === 200) {
          dispatch(FETCH_DATA_CONTENT, { module: 'reports', skip: 0 });
        }
      });
    },
    [RUN_REPORT]({ dispatch }, report) {
      /*
        run the report
     */
      const handleSuccess = (id) => {
        dispatch(FETCH_DATA_CONTENT, { module: 'reports', skip: 0 });
      };

      return dispatch(REQUEST_API, {
        rule: 'reports/send_email',
        method: 'POST',
        data: report,
      }).then((response) => {
        if (response.status === 200) {
          return handleSuccess(report.uuid);
        }
      });
    },
    [DOWNLOAD_REPORT]({ dispatch }, { reportId, name }) {
      return dispatch(REQUEST_API, {
        rule: `reports/${reportId}/pdf`,
        binary: true,
      }).then((response) => {
        downloadFile('pdf', response, name);
      });
    },
  },
};
