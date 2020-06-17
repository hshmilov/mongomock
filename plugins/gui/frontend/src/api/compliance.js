import _get from 'lodash/get';
import createRequest from './create-request';

export const fetchCompliance = async (name, accounts, rules, categories,
  failedOnly, aggregatedView) => {
  const uri = `/compliance/${name}/report`;
  const request = createRequest(uri);

  const requestOptions = {};
  requestOptions.method = 'POST';
  requestOptions.data = {
    accounts,
    rules,
    categories,
    failedOnly,
    aggregatedView,
  };
  const res = await request(requestOptions);
  return res.data;
};

export const fetchComplianceInitialCis = async () => {
  const uri = '/compliance/initial_cis';
  const request = createRequest(uri);

  const requestOptions = {};
  const res = await request(requestOptions);
  return res.data;
};

export const fetchComplianceReportFilters = async (name) => {
  const uri = `/compliance/${name}/filters`;
  const request = createRequest(uri);

  const requestOptions = {};
  const res = await request(requestOptions);
  return res.data;
};

export const sendComplianceEmail = async (name, accounts, mailProperties, schemaFields, cisTitle,
  rules, categories, failedOnly, aggregatedView) => {
  const uri = `/compliance/${name}/send_email`;
  const request = createRequest(uri);

  const requestOptions = {};
  requestOptions.method = 'POST';
  requestOptions.data = {
    name,
    accounts,
    email_properties: mailProperties,
    schema_fields: schemaFields,
    cis_title: cisTitle,
    rules,
    categories,
    failedOnly,
    aggregatedView,
  };

  try {
    const res = await request(requestOptions);
    return res.data;
  } catch (error) {
    const errorMessage = _get(error, 'response.data.message', error.message);
    return Promise.reject(new Error(errorMessage));
  }
};

export const updateComplianceRules = async (name, rules, cisTitle) => {
  const uri = `/compliance/${name}/rules`;
  const request = createRequest(uri);

  const requestOptions = {
    method: 'POST',
    data: { rules, cis_title: cisTitle },
  };
  const res = await request(requestOptions);
  return res.data;
};

export const createJiraIssue = async (name, accounts, jiraProperties, schemaFields, cisTitle,
  rules, categories, failedOnly, aggregatedView) => {
  const uri = `/compliance/${name}/create_jira`;
  const request = createRequest(uri);

  const requestOptions = {
    method: 'POST',
    data: {
      name,
      accounts,
      jira_properties: jiraProperties,
      schema_fields: schemaFields,
      cis_title: cisTitle,
      rules,
      categories,
      failedOnly,
      aggregatedView,
    },
  };

  try {
    const res = await request(requestOptions);
    return res.data;
  } catch (error) {
    const errorMessage = _get(error, 'response.data.message', error.message);
    return Promise.reject(new Error(errorMessage));
  }
};

