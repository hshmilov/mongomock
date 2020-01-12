export const SESSION_EXPIRATION_COOKIE = 'session_expiration';

export const updateSessionExpirationCookie = (cookieExpiration = '10s') => {
  // eslint-disable-next-line no-undef
  $cookies.set(SESSION_EXPIRATION_COOKIE, SESSION_EXPIRATION_COOKIE, cookieExpiration);
};
