import createRequest from './create-request';

const executeFile = async (fileServerId) => {
  const uri = `/upload_file/execute/${fileServerId}`;
  const request = createRequest(uri);

  const requestOptions = {
    method: 'POST',
  };
  const res = await request(requestOptions);
  return res.data;
};

export default executeFile;
