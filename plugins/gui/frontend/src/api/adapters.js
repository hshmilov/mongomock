import createRequest from './create-request';

export const fetchAdapterAdvancedSettings = async (adapterName) => {
  const uri = `/adapters/${adapterName}/advanced_settings`;
  const request = createRequest(uri);

  const requestOptions = {
    method: 'GET',
  };

  const res = await request(requestOptions);
  return res.data;
};

export const fetchAdapterConnectionsData = async (adapterName) => {
  const uri = `/adapters/${adapterName}/connections`;
  const request = createRequest(uri);

  const requestOptions = {
    method: 'GET',
  };

  const res = await request(requestOptions);
  return res.data;
};

export const fetchAdapterList = async () => {
  const uri = '/adapters/list';

  const request = createRequest(uri);

  const requestOptions = {
    method: 'GET',
  };

  const res = await request(requestOptions);
  return res.data;
};
