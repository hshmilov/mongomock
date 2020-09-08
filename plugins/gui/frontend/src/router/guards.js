import store from '@store/index';
import { LOGOUT } from '@store/modules/auth';
import _get from 'lodash/get';

export const adminGuard = (to, from, next) => {
  const user = _get(store, 'state.auth.currentUser.data') || {};

  let unWatch = null;
  const proceed = () => {
    const { role_name: userRole, admin: isAdmin } = _get(store, 'state.auth.currentUser.data') || {};
    if (unWatch) {
      unWatch();
    }
    if (isAdmin
      || userRole === 'Admin') {
      next();
    } else {
      store.dispatch(LOGOUT)
        .then(() => next('/'))
        .catch(() => next('/'));
    }
  };
  // currently there is no way to know if the store load the current user data
  // and got all the info
  // we set a watch on the user_name property and wait for the value
  if (!user.user_name) {
    unWatch = store.watch(
      (state) => {
        const currentUser = _get(state, 'auth.currentUser.data') || {};
        return currentUser.user_name;
      },
      (userName) => {
        if (userName) {
          proceed();
        }
      },
    );
  } else {
    proceed();
  }
};

export const enforcementsFeatureTagGuard = (to, from, next) => {

  const enforcementsLocked = _get(
    store.state,
    'settings.configurable.gui.FeatureFlags.config.enforcement_center',
    null,
  );

  let unWatch = null;
  const proceed = () => {
    if (unWatch) {
      unWatch();
    }
    const curretEnforcementsLocked = !_get(
      store.state,
      'settings.configurable.gui.FeatureFlags.config.enforcement_center',
      null,
    );
    if (!curretEnforcementsLocked) {
      next();
    } else {
      next('/enforcements');
    }
  };
  // When url is loaded, we don't have feature flags yet. Thus, watching it.
  if (enforcementsLocked === null) {
    unWatch = store.watch(
      (state) => state.settings.configurable,
      (configurable) => {
        if (_get(configurable, 'gui.FeatureFlags.config.enforcement_center', null) !== null) {
          proceed();
        }
      },
    );
  } else {
    proceed();
  }
};
