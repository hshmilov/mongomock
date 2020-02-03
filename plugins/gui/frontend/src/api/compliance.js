import createRequest from './create-request';

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
