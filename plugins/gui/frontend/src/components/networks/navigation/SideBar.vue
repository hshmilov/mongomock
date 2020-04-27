<template>
  <aside
    class="x-side-bar"
    :class="{ collapse: collapseSidebar }"
  >
    <div class="x-user">
      <div class="x-user-profile">
        <img :src="userDetails.pic">
        <h5>{{ userDetails.name }}</h5>
      </div>
      <div class="x-user-actions">
        <a
          title="Logout"
          @click="onLogout"
        >
          <svg-icon
            name="navigation/logout"
            height="16"
            :original="true"
          />
        </a>
        <router-link
          :to="{name: 'My Account'}"
          active-class="active"
          title="My Account"
          @click.native="$emit('click')"
        >
          <svg-icon
            name="navigation/settings"
            height="16"
            :original="true"
          />
        </router-link>
      </div>
    </div>
    <x-nav v-if="isFeatureFlagsLoaded">
      <x-nav-item
        v-bind="navigationProps('Dashboard', 'dashboard')"
        :exact="true"
      />
      <x-nav-item
        v-bind="navigationProps('Devices', 'devices', null, $permissionConsts.categories.DevicesAssets)"
      />
      <x-nav-item
        v-bind="navigationProps('Users', 'users', null, $permissionConsts.categories.UsersAssets)"
      />
      <x-nav-item
        v-if="isComplianceVisible"
        v-bind="navigationProps('Cloud Asset Compliance', 'compliance', 'Cloud Compliance')"
      />
      <x-nav-item v-bind="navigationProps('Enforcements', 'enforcements', 'Enforcement Center')" />
      <x-nav-item v-bind="navigationProps('Adapters', 'adapters')" />
      <x-nav-item v-bind="navigationProps('Reports', 'reports')" />
      <x-nav-item v-bind="navigationProps('Activity Logs', 'audit')" />
      <x-nav-item v-bind="navigationProps('Instances', 'instances')" />
    </x-nav>
  </aside>
</template>

<script>
import { mapState, mapActions, mapMutations } from 'vuex';
import _invert from 'lodash/invert';
import _get from 'lodash/get';
import { REMOVE_TOASTER } from '@store/mutations';
import xNav from '../../axons/menus/Nav.vue';
import xNavItem from '../../axons/menus/NavItem.vue';
import { LOGOUT } from '../../../store/modules/auth';


export default {
  name: 'XSideBar',
  components: { xNav, xNavItem },
  computed: {
    ...mapState({
      featureFlags(state) {
        const featureFlasConfigs = _get(state, 'settings.configurable.gui.FeatureFlags.config', null);
        return featureFlasConfigs;
      },
      userDetails(state) {
        return {
          name: `${state.auth.currentUser.data.first_name} ${state.auth.currentUser.data.last_name}`,
          pic: state.auth.currentUser.data.pic_name,
        };
      },
      userPermissions(state) {
        return state.auth.currentUser.data.permissions;
      },
      collapseSidebar(state) {
        return state.interaction.collapseSidebar;
      },
    }),
    permissionCategoriesMap() {
      return _invert(this.$permissionConsts.categories);
    },
    isFeatureFlagsLoaded() {
      return this.featureFlags;
    },
    isComplianceVisible() {
      return this.featureFlags && this.featureFlags.cloud_compliance
        ? this.featureFlags.cloud_compliance.enabled : false;
    },
    logoSize: {
      get() {
        return this.collapseSidebar ? '47' : '114';
      },
    },
  },
  methods: {
    ...mapActions({
      logout: LOGOUT,
    }),
    ...mapMutations({
      removeToaster: REMOVE_TOASTER,
    }),
    navigationProps(name, id, title, permissionCategory) {
      let currentPermissionCategory = permissionCategory;
      if (!currentPermissionCategory && this.permissionCategoriesMap[id]) {
        currentPermissionCategory = id;
      }
      const restricted = this.$cannot(currentPermissionCategory,
        this.$permissionConsts.actions.View);
      return {
        id,
        name,
        title,
        icon: id,
        disabled: restricted,
        clickHandler: restricted ? this.notifyAccess : undefined,
      };
    },
    notifyAccess(name) {
      this.$emit('access-violation', name);
    },
    onLogout() {
      this.removeToaster();
      this.logout().then(() => {
        this.$router.push('/');
      });
    },
  },
};
</script>

<style lang="scss">
    .x-side-bar {
        position: fixed;
        top: 0;
        width: 240px;
        transition: all ease-in 0.2s;
        height: 100%;
        z-index: 100;
        background: $theme-black;
        padding: 60px 0;
        display: flex;
        flex-flow: column;

        .x-user {
            flex: 0 1 auto;
            position: relative;
            font-size: 16px;
            width: 100%;
            overflow-x: hidden;
            transition: all ease-in 0.2s;
            margin-bottom: 48px;

            .x-user-profile {
                text-align: center;
                margin: 0 auto;
                padding: 10px 0 5px 0;
                border-radius: 100%;
                width: 240px;

                img {
                    width: 60px;
                    margin-bottom: 8px;
                    border-radius: 100%;
                }

                h5 {
                    color: $theme-white;
                    margin-bottom: 0;
                    transition: all ease-in 0.2s;
                }
            }

            .x-user-actions {
                padding: 4px 0px;
                position: relative;
                text-align: center;

                > a {
                    color: $grey-4;
                    padding: 0 4px;

                    .svg-fill {
                        fill: $grey-4;
                    }

                    .svg-stroke {
                        stroke: $grey-4;
                    }

                    &:hover, &.active {
                        color: $theme-white;

                        .svg-fill {
                            fill: $theme-white;
                        }

                        .svg-stroke {
                            stroke: $theme-white;
                        }
                    }

                    &:after {
                        display: none;
                    }
                }
            }
        }

        > .x-nav {
            width: 100%;

            > .x-nav-item {
                border-left: 2px solid transparent;

                > .item-link {
                    width: 100%;
                    height: 40px;
                    text-align: left;
                }

                &.active {
                    border-left: 2px solid $theme-orange;
                }

                .x-nav {
                    display: none;

                }

                &.active > .x-nav {
                    display: block;
                }
            }
        }
    }

    .x-side-bar.collapse {
        display: block;
        width: 60px;
        padding-bottom: 0;

        .x-user {
            .x-user-profile {
                text-align: left;

                h5 {
                    opacity: 0;
                }
            }
        }
    }

    .x-side-bar.collapse .x-nav {
        overflow: visible;
    }
</style>
