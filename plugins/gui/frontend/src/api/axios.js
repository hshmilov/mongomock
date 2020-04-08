import axios from 'axios';

/*
  A main axios client instance initialization for use in all of the Vue code
  handles the baseURL automatically and adds the desired request and response headers
  using axios interceptors.
*/

let host = '';
const excludedUrls = ['login', 'signup', 'login/ldap', 'login/saml'];
if (process.env.NODE_ENV === 'development') {
  host = 'https://127.0.0.1';
}

const requestConfig = {
  baseURL: `${host}/api/`,
};

if (process.env.NODE_ENV === 'development') {
  requestConfig.withCredentials = true;
}

const axiosClient = axios.create(requestConfig);

axiosClient.interceptors.request.use((config) => {
  if (['post', 'put', 'delete', 'patch'].includes(config.method) && !excludedUrls.includes(config.url)) {
    return axiosClient.get('csrf').then((response) => {
      // eslint-disable-next-line no-param-reassign
      config.headers['X-CSRF-Token'] = response.data;
      return config;
    });
  }
  return config;
}, (error) => Promise.reject(error));


export default axiosClient;
