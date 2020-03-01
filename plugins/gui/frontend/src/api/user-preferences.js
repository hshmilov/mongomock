import createRequest from './create-request';
import _get from 'lodash/get';

export const saveDefaultTableColumns = async (entity, fields) => {
  const uri = '/system/users/self/preferences';
  const request = createRequest(uri);
  const requestOptions = {
    method: 'POST',
    data: {
      [entity]: {
        table_columns: {
          default: fields,
        },
      },
    },
  };
  const res = await request(requestOptions);
  return res.data;
};

export const getDefaultTableColumns = async (entity) => {
  const uri = '/system/users/self/preferences';
  const request = createRequest(uri);
  const { data } = await request({});
  return _get(data, `${entity}.table_columns.default`, []);
};
