import axios from 'axios';
import jwt_decode from 'jwt-decode';
import {Mutex} from 'async-mutex';
import {ACCESS_TOKEN, REFRESH_TOKEN} from '@constants/session_utils';

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
const inRequestMutex = new Mutex();
let releaseMutex = null;

async function refreshAccessToken(refreshToken) {
  let token = null;
  try {
    const response = await axiosClient.get('token/refresh', {
      headers: {
        Authorization: `Bearer ${refreshToken}`,
      },
    });
    if (response.status === 200) {
      localStorage.setItem(ACCESS_TOKEN, response.data.access_token);
      token = response.data.access_token;
    }
  } catch (error) {
    // If there is an error with the refresh clear to tokens in order to go to login page
    localStorage.removeItem(ACCESS_TOKEN);
    localStorage.removeItem(REFRESH_TOKEN);
  }
  return token;
}

function clearReleaseMutex() {
  if (releaseMutex) {
    releaseMutex();
    releaseMutex = null;
  }
}

async function checkTokenExpirationAndRefreshIfNeeded(token) {
  let validToken = token;
  const { exp } = jwt_decode(validToken);
  if (Date.now() >= exp * 1000) {
    releaseMutex = await inRequestMutex.acquire();
    validToken = localStorage.getItem(ACCESS_TOKEN);
    const doubleCheckExp = jwt_decode(token).exp;
    if (Date.now() >= doubleCheckExp * 1000) {
      const refreshToken = localStorage.getItem(REFRESH_TOKEN);
      if (refreshToken) {
        validToken = await refreshAccessToken(refreshToken);
      }
    }
    clearReleaseMutex();
  }
  return validToken;
}

axiosClient.interceptors.request.use(async (config) => {
  let token = localStorage.getItem(ACCESS_TOKEN);
  if (config.url === 'token/refresh') {
    token = localStorage.getItem(REFRESH_TOKEN);
  } else if (token) {
    token = await checkTokenExpirationAndRefreshIfNeeded(token);
  }
  if (token) {
    // eslint-disable-next-line no-param-reassign
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  clearReleaseMutex();
  return Promise.reject(error);
});

axiosClient.interceptors.response.use((response) => {
  // Saving the server time for futher use in the code
  if (response.headers.date) {
    serverTime = response.headers.date;
  }
  return response;
}, (error) => {
  clearReleaseMutex();
  return Promise.reject(error);
});
