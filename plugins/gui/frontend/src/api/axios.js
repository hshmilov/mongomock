import axios from 'axios'

/*
  A main axios client instance initialization for use in all of the Vue code
  handles the baseURL automatically and adds the desired request and response headers
  using axios interceptors.
*/

let host = ''
let excluded_urls = ['login', 'signup', 'login/ldap', 'login/saml']
if (process.env.NODE_ENV === 'development') {
  host = 'https://127.0.0.1'
}
const axios_client = axios.create({
  baseURL : host + '/api/'
});

axios_client.interceptors.request.use(function (config) {
  if (['post', 'put', 'delete', 'patch'].includes(config.method) && !excluded_urls.includes(config.url)) {
    return axios_client.get('csrf').then(response => {
      config.headers['X-CSRF-Token'] = response.data;
      return config
    });
  }
  return config;
}, function (error) {
  return Promise.reject(error);
});

export default axios_client;