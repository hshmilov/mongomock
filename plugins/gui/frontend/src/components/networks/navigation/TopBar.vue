<template>
  <header
    class="x-top-bar"
    :class="{ 'minimize': collapseSidebar }"
  >
    <div
      class="bar-toggle"
      @click="toggleSidebar"
    >
      <MdIcon md-src="/src/assets/icons/navigation/menu.svg" />
    </div>
    <div
      class="bar-logo"
    >
      <SvgIcon
        name="logo/logo"
        height="30"
        :original="true"
      />
      <SvgIcon
        name="logo/axonius"
        height="16"
        :original="true"
      />
    </div>
    <XTrialBanner />
    <XContractBanner />
    <ul class="bar-nav">
      <li class="nav-item">
        <button
          v-if="researchStatusLocal === 'starting'"
          class="item-link research-link"
          disabled
        >
          <MdIcon
            md-src="/src/assets/icons/symbol/running.svg"
            class="rotating"
          />
          <div>Initiating...</div>
        </button>
        <button
          v-else-if="researchStatusLocal === 'stopping'"
          class="item-link research-link"
          disabled
          @click="stopResearchNow"
        >
          <MdIcon
            md-src="/src/assets/icons/symbol/running.svg"
            class="rotating"
          />
          <div>Stopping...</div>
        </button>
        <button
          v-else-if="researchStatusLocal !== 'running'"
          id="run_research"
          class="item-link research-link"
          :disabled="!isDashboardWrite"
          @click="startResearchNow"
        >
          <MdIcon md-src="/src/assets/icons/action/start.svg" />
          <div>Discover Now</div>
        </button>
        <button
          v-else-if="researchStatusLocal === 'running'"
          id="stop_research"
          class="item-link research-link"
          :disabled="!isDashboardWrite"
          @click="stopResearchNow"
        >
          <MdIcon md-src="/src/assets/icons/action/stop.svg" />
          <div>Stop Discovery</div>
        </button>
      </li>
      <li class="nav-item">
        <a class="item-link">
          <XNotificationPeek v-if="!isExpired" />
          <SvgIcon
            v-else
            name="navigation/notifications"
            :original="true"
            height="20"
          />
        </a>
      </li>
      <li
        class="nav-item"
        :class="{ disabled: isSettingsRestricted}"
      >
        <a
          id="settings"
          class="item-link"
          @click="navigateSettings"
        >
          <SvgIcon
            name="navigation/settings"
            :original="true"
            height="20"
          />
        </a>
        <XTipInfo
          v-if="isEmptySetting('mail')"
          content="In order to send alerts through mail, configure it under settings"
          @dismiss="dismissEmptySetting('mail')"
        />
        <XTipInfo
          v-if="isEmptySetting('syslog')"
          content="In order to send alerts through a syslog system, configure it under settings"
          @dismiss="dismissEmptySetting('syslog')"
        />
        <XTipInfo
          v-if="isEmptySetting('httpsLog')"
          content="In order to send alerts through an HTTPS log system, configure it under settings"
          @dismiss="dismissEmptySetting('httpsLog')"
        />
        <XTipInfo
          v-if="isEmptySetting('serviceNow')"
          content="In order to create a ServiceNow computer or incident, configure it under settings"
          @dismiss="dismissEmptySetting('serviceNow')"
        />
        <XTipInfo
          v-if="isEmptySetting('freshService')"
          content="In order to create a FreshService incident, configure it under settings"
          @dismiss="dismissEmptySetting('freshService')"
        />
        <XTipInfo
          v-if="isEmptySetting('jira')"
          content="In order to create a Jira incident, configure it under settings"
          @dismiss="dismissEmptySetting('jira')"
        />
        <XTipInfo
          v-if="isEmptySetting('opsgenie')"
          content="In order to create an Opsgenie incident, configure it under settings"
          @dismiss="dismissEmptySetting('opsgenie')"
        />
      </li>
    </ul>
  </header>
</template>

<script>
import {
  mapState, mapGetters, mapMutations, mapActions,
} from 'vuex';
import XNotificationPeek from '../NotificationsPeek.vue';
import XTipInfo from '../onboard/TipInfo.vue';
import XTrialBanner from '../onboard/TrialBanner.vue';
import XContractBanner from '../onboard/ContractBanner.vue';

import { FETCH_LIFECYCLE } from '../../../store/modules/dashboard';
import { UPDATE_EMPTY_STATE } from '../../../store/modules/onboarding';
import { IS_EXPIRED } from '../../../store/getters';
import { TOGGLE_SIDEBAR } from '../../../store/mutations';
import { START_RESEARCH_PHASE, STOP_RESEARCH_PHASE, FETCH_DATA_FIELDS } from '../../../store/actions';
import { entities } from '../../../constants/entities';

export default {
  name: 'XTopBar',
  components: {
    XNotificationPeek, XTipInfo, XTrialBanner, XContractBanner,
  },
  data() {
    return {
      isDown: false,
      researchStatusLocal: '',
    };
  },
  computed: {
    ...mapState({
      collapseSidebar(state) {
        return state.interaction.collapseSidebar;
      },
      emptySettings(state) {
        return state.onboarding.emptyStates.settings;
      },
      researchStatus(state) {
        return state.dashboard.lifecycle.data.status;
      },
      isSettingsRestricted(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Settings === 'Restricted';
      },
      isDashboardWrite(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Dashboard === 'ReadWrite' || user.admin;
      },
      userPermissions(state) {
        return state.auth.currentUser.data.permissions;
      },
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
    }),
    anyEmptySettings() {
      return Object.values(this.emptySettings).find((value) => value);
    },
  },
  mounted() {
    const updateLifecycle = () => {
      this.fetchLifecycle().then(() => {
        if (this._isDestroyed) return;
        if (this.expired) return;
        if ((this.researchStatusLocal !== ''
                  && this.researchStatusLocal !== 'done'
                  && this.researchStatus === 'done')
            || (this.researchStatusLocal === '' && this.researchStatus === 'running')) {
          entities.forEach((entity) => {
            if (this.entityRestricted(entity.title)) return;
            this.fetchDataFields({ module: entity.name });
          });
        }
        this.researchStatusLocal = this.researchStatus;
        this.timer = setTimeout(updateLifecycle, 3000);
      });
    };
    updateLifecycle();
  },
  beforeDestroy() {
    clearTimeout(this.timer);
  },
  methods: {
    ...mapMutations({
      toggleSidebar: TOGGLE_SIDEBAR, updateEmptyState: UPDATE_EMPTY_STATE,
    }),
    ...mapActions({
      fetchLifecycle: FETCH_LIFECYCLE,
      startResearch: START_RESEARCH_PHASE,
      stopResearch: STOP_RESEARCH_PHASE,
      fetchDataFields: FETCH_DATA_FIELDS,

    }),
    startResearchNow() {
      this.$ga.event('research', 'start-now', '', 1);
      this.researchStatusLocal = 'starting';
      this.startResearch().catch(() => this.researchStatusLocal = '');
    },
    stopResearchNow() {
      this.$ga.event('research', 'stop-now', '', 1);
      this.researchStatusLocal = 'stopping';
      this.stopResearch().catch(() => this.researchStatusLocal = 'running');
    },
    navigateSettings() {
      if (this.isSettingsRestricted) {
        this.$emit('access-violation', name);
        return;
      }
      if (this.anyEmptySettings) {
        this.$router.push({ path: '/settings#global-settings-tab' });
        this.dismissAllSettings();
      } else {
        this.$router.push({ name: 'Settings' });
      }
    },
    entityRestricted(entity) {
      return this.userPermissions[entity] === 'Restricted';
    },
    isEmptySetting(name) {
      return this.emptySettings[name];
    },
    dismissEmptySetting(name) {
      this.updateEmptyState({
        settings: {
          [name]: false,
        },
      });
    },
    dismissAllSettings() {
      this.updateEmptyState({
        settings: Object.keys(this.emptySettings).reduce((map, setting) => {
          map[setting] = false;
          return map;
        }, {}),
      });
    },
  },
};
</script>

<style lang="scss">
    .x-top-bar {
        background: $grey-0;
        position: fixed;
        top: 0;
        width: 100%;
        z-index: 1000;
        display: flex;
        height: 60px;

        .bar-toggle {
            line-height: 60px;
            width: 240px;
            background-color: $theme-black;
            transition: all ease-in 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;

            .svg-stroke {
                stroke: $grey-4;
            }

            .svg-fill {
                fill: $grey-4;
            }

            &:hover {
                .svg-stroke {
                    stroke: $theme-orange;
                }

                .svg-fill {
                    fill: $theme-orange;
                }
            }
        }

        .bar-logo {
            margin-left: 24px;
            line-height: 60px;
        }

        .bar-nav {
            flex: 1 0 auto;
            display: flex;
            justify-content: flex-end;
            list-style: none;
            margin-right: 12px;

            > .nav-item {
                margin: auto 12px;
                line-height: 60px;

                .svg-stroke {
                    stroke: $theme-orange;
                }

                .svg-fill {
                    fill: $theme-orange;
                }

                &.disabled .item-link, &.disabled .item-link:hover {
                    cursor: default;

                    .svg-stroke {
                        stroke: $grey-2;
                    }

                    .svg-fill {
                        fill: $grey-2;
                    }
                }

                .item-link {
                    .svg-fill {
                        fill: $theme-black;
                    }

                    .svg-stroke {
                        stroke: $theme-black;
                    }

                    &:hover {
                        .svg-stroke {
                            stroke: $theme-orange;
                        }

                        .svg-fill {
                            fill: $theme-orange;
                        }
                    }

                    &.research-link {
                        background: $theme-black;
                        color: $grey-1;
                        border-radius: 16px;
                        display: flex;
                        align-items: center;
                        padding: 0 16px 0 12px;
                        line-height: 32px;
                        font-size: 14px;
                        cursor: pointer;
                        box-shadow: none;
                        border: 0;
                        font-weight: 400;
                        font-family: $font-stack;

                        .md-icon {
                          height: 20px;
                          display: flex;
                        }

                        .svg-fill {
                            fill: $grey-1;
                            margin-right: 8px;
                        }

                        &:hover .svg-fill, .rotating .svg-fill {
                            fill: $theme-orange;
                        }

                        .svg-stroke {
                            stroke: $theme-orange;
                        }

                        &:disabled {
                            cursor: default;
                            background-color: rgba($theme-black, 0.4);

                            &:hover .svg-fill {
                                fill: $grey-1;
                            }
                        }
                    }

                    &.disabled {
                        cursor: default;
                    }
                }
            }
        }

        .banner-overlay {
            position: fixed;
            z-index: 1000;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, .6);
            transition: opacity .3s ease;
        }
    }

    .x-top-bar.minimize {
        .bar-toggle {
            width: 60px;
        }
    }

</style>
