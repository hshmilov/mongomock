import qs from 'qs';
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

export const fetchChartData = async (params) => {
  const {
    uuid, historical, skip, limit, search, refresh, sortBy, sortOrder, blocking,
  } = params;

  const uri = `/dashboard/charts/${uuid}`;
  const qsParams = {
    to_date: historical,
    from_date: historical,
    skip,
    limit,
    search,
    refresh,
    blocking,
    sort_by: sortBy,
    sort_order: sortOrder,
  };
  const querystring = qs.stringify(qsParams, { addQueryPrefix: true, skipNulls: true });
  const request = createRequest(uri + querystring);
  const requestOptions = {
    method: 'GET',
  };

  const res = await request(requestOptions);
  return res;
};
