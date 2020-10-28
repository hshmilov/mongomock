// eslint-disable-next-line import/prefer-default-export
export const UPDATE_COMPLIANCE_FILTERS = 'UPDATE_COMPLIANCE_FILTERS';
export const UPDATE_COMPLIANCE_VIEW = 'UPDATE_COMPLIANCE_VIEW';

const getComplianceReportState = () => {
  return {
    content: { data: [], fetching: false, error: '' },
    count: { data: 0, fetching: false, error: '' },
    view: {
      page: 0,
      pageSize: 50,
      query: {
        filter: '', expressions: [],
      },
      filters: {
        accounts: [], rules: [], categories: [], failedOnly: false, aggregatedView: true,
      },
    },
  };
};

export const compliance = {
  state: {
    /* Compliance DataTable State */
    failedOnly: false,
    content: { data: [], fetching: false, error: '' },
    allCloudComplianceRules: [],
    count: { data: 0, fetching: false, error: '' },
    cis: {
      aws: {
        report: getComplianceReportState(),
      },
      azure: {
        report: getComplianceReportState(),
      },
      oracle_cloud: {
        report: getComplianceReportState(),
      },
    },
    view: {
      page: 0,
      pageSize: 20,
      schema_fields: [{
        name: 'status', title: '', type: 'string', format: 'status', order: 1,
      }, {
        name: 'section', title: 'Section', type: 'string', order: 2,
      }, {
        name: 'rule', title: 'Rule', type: 'string', order: 3,
      }, {
        name: 'category', title: 'Category', type: 'string', order: 4,
      }, {
        name: 'account', title: 'Account', type: 'array', order: 5, items: { type: 'string' },
      }, {
        name: 'description', title: 'Description', type: 'text', expanded: true, order: 6,
      }, {
        name: 'remediation', title: 'Remediation', type: 'text', expanded: false, order: 7,
      }, {
        name: 'results', title: 'Results (Failed/Checked)', type: 'string', order: 8,
      }, {
        name: 'entities_results', title: 'Results', type: 'text', expanded: true, order: 9,
      }, {
        name: 'affected', title: 'Affected Devices/Users', type: 'integer', order: 10,
      }, {
        name: 'cis', title: 'CIS Controls', type: 'text', expanded: true, order: 11,
      }, {
        name: 'last_updated', title: 'Last Updated', type: 'text', format: 'date-time', expanded: true, order: 12,
      }, {
        name: 'comments_csv', title: 'Comments', type: 'text', expanded: true, order: 13,
      }],
      coloumnSizes: [],
      query: {
        filter: '', expressions: [],
      },
      sort: {
        field: '', desc: true,
      },
    },
    /* Data of Rule currently being shown */
    current: { fetching: false, data: {}, error: '' },
  },
  mutations: {
    [UPDATE_COMPLIANCE_FILTERS](state, payload) {
      const { cisName, filterName, value } = payload;
      state.cis[cisName].report.view.filters = {
        ...state.cis[cisName].report.view.filters,
        [filterName]: value,
      };
    },
    [UPDATE_COMPLIANCE_VIEW](state, payload) {
      const { cisName } = payload;
      state.cis[cisName].report.view = {
        ...state.cis[cisName].report.view,
        page: 0,
      };
    },
  },
};
