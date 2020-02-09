import axios from 'axios';
import store from '@store/index';
import _merge from 'lodash/merge';
import { INIT_USER } from '@store/modules/auth';

let host = '';
if (process.env.NODE_ENV === 'development') {
  host = 'https://127.0.0.1';
}
const baseURL = `${host}/api`;

export default (uri, baseOptions = {}) => async ({
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
  try {
    return await axios(allOptions);
  } catch (error) {
    if (error && error.response) {
      const errorMessage = error.response.data.message;
      if (error.response.status === 401) {
        store.commit(INIT_USER, { fetching: false, error: errorMessage });
      }
    }
    throw error;
  }
};
