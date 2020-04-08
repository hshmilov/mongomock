import _get from 'lodash/get';
import createRequest from './create-request';

export const saveUserTableColumnGroup = async (entity, fields, columnGroupName = 'default') => {
  const uri = '/settings/users/self/preferences';
  const request = createRequest(uri);
  const requestOptions = {
    method: 'POST',
    data: {
      [entity]: {
        table_columns: {
          [columnGroupName]: fields,
        },
      },
    },
  };
  const res = await request(requestOptions);
  return res.data;
};

export const getUserTableColumnGroups = async (entity) => {
  const uri = '/settings/users/self/preferences';
  const request = createRequest(uri);
  const { data } = await request({});
  return _get(data, `${entity}.table_columns`, {});
};
