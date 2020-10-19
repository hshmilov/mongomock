import createRequest from './create-request';

export const fetchReport = async (reportId) => {
  const uri = `/reports/${reportId}`;
  const request = createRequest(uri, {}, true);

  const requestOptions = {
    method: 'GET',
  };

  const res = await request(requestOptions);
  return res.data;
};
