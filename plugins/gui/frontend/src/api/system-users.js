import createRequest from './create-request';

const baseURI = '/settings/users';
// eslint-disable-next-line import/prefer-default-export
export const fetchUsernamesList = async () => {
  const uri = `${baseURI}/username_list`;
  const request = createRequest(uri);
  const requestOptions = {
    method: 'GET',
  };
  const res = await request(requestOptions);
  return res.data;
};
