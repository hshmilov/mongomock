import createRequest from './create-request';

const baseURI = '/settings/roles';
// eslint-disable-next-line import/prefer-default-export
export const getRoleUserCount = async (roleId) => {
  const uri = `${baseURI}/${roleId}/assignees`;
  const request = createRequest(uri);
  const requestOptions = {
    method: 'GET',
  };
  const res = await request(requestOptions);
  return res.data;
};

export const fetchAssignableRolesList = async () => {
  const uri = `${baseURI}/assignable_roles`;
  const request = createRequest(uri);
  const requestOptions = {
    method: 'GET',
  };
  const res = await request(requestOptions);
  return res.data;
};
