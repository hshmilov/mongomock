import createRequest from './create-request';
import _get from 'lodash/get';

export const fetchCompliance = async (name, accounts) => {
  const uri = `/compliance/${name}/report`;
  const request = createRequest(uri);

  const requestOptions = {};
  requestOptions.method = 'POST';
  requestOptions.data = {
    accounts,
  };
  const res = await request(requestOptions);
  return res.data;
};

export const fetchComplianceAccounts = async (name) => {
  const uri = `/compliance/${name}/accounts`;
  const request = createRequest(uri);

  const requestOptions = {};
  const res = await request(requestOptions);
  return res.data;
};

export const sendComplianceEmail = async (name, accounts, mailProperties, schemaFields, cisTitle) => {
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
  };

  try {
    const res = await request(requestOptions);
    return res.data;
  } catch (error) {
    const errorMessage = _get(error, 'response.data.message', error.message);
    return Promise.reject(new Error(errorMessage));
  }
};
