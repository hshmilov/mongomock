import axios from 'axios';
import {ACCESS_TOKEN, REFRESH_TOKEN} from "@constants/session_utils";

/*
  A main axios client instance initialization for use in all of the Vue code
  handles the baseURL automatically and adds the desired request and response headers
  using axios interceptors.
*/

let host = '';
if (process.env.NODE_ENV === 'development') {
  // as defined in ports.py for gui service
  host = 'https://127.0.0.1:4433';
}

const requestConfig = {
  baseURL: `${host}/api/`,
};

if (process.env.NODE_ENV === 'development') {
  requestConfig.withCredentials = true;
}

const axiosClient = axios.create(requestConfig);
export default axiosClient;
export let serverTime = 0;

axiosClient.interceptors.request.use((config) => {
  let token = localStorage.getItem(ACCESS_TOKEN);
  if (config.url === 'token/refresh') {
    token = localStorage.getItem(REFRESH_TOKEN);
  }
  if (token) {
    // eslint-disable-next-line no-param-reassign
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

axiosClient.interceptors.response.use((response) => {
  // Saving the server time for futher use in the code
  if (response.headers.date) {
    serverTime = response.headers.date;
  }
  return response;
}, (error) => Promise.reject(error));
