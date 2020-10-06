import qs from 'qs';
import _mapKeys from 'lodash/mapKeys';
import _snakeCase from 'lodash/snakeCase';
import createRequest from './create-request';

export const isEmptySystem = async () => {
  const uri = '/dashboard/is_system_empty';
  const request = createRequest(uri);

  const requestOptions = {
    method: 'GET',
  };

  const res = await request(requestOptions);
  return res.data;
};

export const getCurrentSpaceData = async (spaceId) => {
  const uri = `/dashboard/${spaceId}`;
  const request = createRequest(uri);

  const requestOptions = {
    method: 'GET',
  };

  const res = await request(requestOptions);
  return res.data;
};

function pythonizeKeys(value, key) {
  return _snakeCase(key);
}

export const fetchChartData = async (params) => {
  const {
    uuid,
    ...restParams
  } = params;

  const uri = `/dashboard/charts/${uuid}`;

  const qsParams = _mapKeys(restParams, pythonizeKeys);

  const querystring = qs.stringify(qsParams, { addQueryPrefix: true, skipNulls: true });
  const request = createRequest(uri + querystring);
  const requestOptions = {
    method: 'GET',
  };

  const res = await request(requestOptions);
  return res;
};
