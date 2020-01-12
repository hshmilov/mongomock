import { mapState, mapActions } from 'vuex';
import ifvisible from 'ifvisible';
import { LOGOUT } from '../store/modules/auth';
import { SESSION_EXPIRATION_COOKIE, updateSessionExpirationCookie } from '../constants/session_utils';

export const IDLE_STATUS = 'idle';
export const HIDDEN_STATUS = 'hidden';
export const ACTIVE_STATUS = 'active';

export default {
  data() {
    return {
      sessionStatus: ACTIVE_STATUS,
      showMessage: false,
      activeTimeout: null,
      hiddenTimeout: null,
      idleTimeout: null,
    };
  },
  computed: {
    ...mapState({
      timeout(state) {
        return state.auth.currentUser.data.timeout;
      },
    }),
  },
  watch: {
    timeout() {
      this.initSessionTimeout();
    },
  },
  methods: {
    ...mapActions({
      logout: LOGOUT,
    }),
    initSessionTimeout() {
      if (!this.timeout) {
        return;
      }

      if (!this.isSessionCookieValid()) {
        this.onLogout();
        return;
      }
      this.clearTimeouts();
      ifvisible.setIdleDuration(this.timeout * 60);
      ifvisible.on('statusChanged', (e) => {
        this.handleUserSessionStatus({
          status: e.status,
        });
      });
      this.handleActiveSession(this.timeout + 'min');
      window.onbeforeunload = () => {
        this.clearTimeouts();
        if (this.sessionStatus === ACTIVE_STATUS) {
          updateSessionExpirationCookie(this.timeout + 'min');
        }
      };
    },
    handleUserSessionStatus(payload) {
      this.sessionStatus = payload.status;
      this.clearTimeouts();
      if (this.sessionStatus === IDLE_STATUS) {
        // Delay the first idle check in order to let the expiration cookie to expire
        this.handleIdleSession(1000);
      } else if (this.sessionStatus === HIDDEN_STATUS) {
        this.handleHiddenSession(this.timeout * 60 * 1000);
      } else {
        this.handleActiveSession(this.timeout + 'min');
      }
    },
    handleActiveSession(cookieExpiration) {
      // Set cookie only if session is still active
      if (this.sessionStatus === ACTIVE_STATUS) {
        updateSessionExpirationCookie(cookieExpiration);
        this.activeTimeout = setTimeout(() => {
          // Check activity every 10 sec after the initial session start
          this.handleActiveSession('10s');
        }, 9000); // next active check will be in 9 sec so the cookie won't expire before renewed
      }
    },
    handleHiddenSession(timeout) {
      this.hiddenTimeout = setTimeout(() => {
        if (!this.isSessionCookieValid()) {
          this.onLogout();
        } else {
          this.handleHiddenSession(1000 * 60);
        }
      }, timeout);
    },
    handleIdleSession(timeout) {
      this.idleTimeout = setTimeout(() => {
        // Check the expiration cookie - in case the session is still active in other tabs
        if (!this.isSessionCookieValid()) {
          this.onLogout();
        } else {
          // Check every second after the current session turns Idle
          this.handleIdleSession(1000);
        }
      }, timeout);
    },
    onLogout() {
      this.clearTimeouts();
      this.logout({ userTimedOut: true });
    },
    clearTimeouts() {
      if (this.hiddenTimeout) {
        clearTimeout(this.hiddenTimeout);
      }
      if (this.activeTimeout) {
        clearTimeout(this.activeTimeout);
      }
      if (this.idleTimeout) {
        clearTimeout(this.idleTimeout);
      }
    },
    isSessionCookieValid() {
      return !this.timeout || this.$cookies.isKey(SESSION_EXPIRATION_COOKIE);
    },
  },
};
