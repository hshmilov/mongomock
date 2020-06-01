// eslint-disable-next-line import/prefer-default-export
export const compliance = {
  state: {
    /* Compliance DataTable State */
    failedOnly: false,
    content: { data: [], fetching: false, error: '' },
    allCloudComplianceRules: [],
    count: { data: 0, fetching: false, error: '' },
    cis_aws: {
      report: {
        content: { data: [], fetching: false, error: '' },
        count: { data: 0, fetching: false, error: '' },
        view: {
          page: 0,
          pageSize: 50,
          query: {
            filter: '', expressions: [],
          },
        },
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
        name: 'account', title: 'Account', type: 'string', order: 5,
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
};
