import axios from 'axios';
import _merge from 'lodash/merge';

let host = '';
if (process.env.NODE_ENV === 'development') {
  host = 'https://127.0.0.1';
}
const baseURL = `${host}/api`;

export default (uri, baseOptions = {}) => ({
  method = 'GET',
  data,
  binary,
  params,
  options = {},
  headers,
}) => {
  const base = {
    url: `${baseURL}${uri}`,
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  if (data) {
    base.data = data;
  }

  if (binary) {
    base.responseType = 'arraybuffer';
  }

  if (params) {
    base.params = params;
  }

  if (headers) {
    base.headers = _merge(base.headers, headers);
  }


  const allOptions = _merge(baseOptions, base, options);
  return axios(allOptions);
};
