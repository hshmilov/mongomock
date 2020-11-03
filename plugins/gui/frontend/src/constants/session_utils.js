export const SESSION_EXPIRATION_COOKIE = 'session_expiration';
// set the default jwt token refresh to 9 minutes
export const DEFAULT_TOKEN_REFRESH_TIMEOUT = 9 * 60;

export const ACCESS_TOKEN = 'access_token';
export const REFRESH_TOKEN = 'refresh_token';
export const SAML_TOKEN = 'saml_token';
export const CURRENT_PATH = 'currentPath';

export const updateSessionExpirationCookie = (cookieExpiration = '10s') => {
  // eslint-disable-next-line no-undef
  $cookies.set(SESSION_EXPIRATION_COOKIE, SESSION_EXPIRATION_COOKIE, cookieExpiration);
};
