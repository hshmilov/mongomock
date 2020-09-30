<template>
  <header
    class="x-top-bar"
    :class="{ 'minimize': collapseSidebar }"
  >
    <div
      class="bar-toggle"
      @click="toggleSidebar"
    >
      <XIcon
        family="navigation"
        type="menu"
      />
    </div>
    <div
      class="bar-logo"
    >
      <XIcon
        family="logo"
        type="logo"
        class="icon"
      />
      <XIcon
        family="logo"
        type="axonius"
        class="name"
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
          <XIcon
            family="symbol"
            type="running"
            spin
          />
          <div>Initiating...</div>
        </button>
        <button
          v-else-if="researchStatusLocal === 'stopping'"
          class="item-link research-link"
          disabled
          @click="stopResearchNow"
        >
          <XIcon
            family="symbol"
            type="running"
            spin
          />
          <div>Stopping...</div>
        </button>
        <button
          v-else-if="researchStatusLocal !== 'running'"
          id="run_research"
          class="item-link research-link"
          :disabled="cannotRunDiscovery"
          @click="startResearchNow"
        >
          <XIcon
            family="action"
            type="start"
          />
          <div>Discover Now</div>
        </button>
        <button
          v-else-if="researchStatusLocal === 'running'"
          id="stop_research"
          class="item-link research-link"
          :disabled="cannotRunDiscovery"
          @click="stopResearchNow"
        >
          <XIcon
            family="action"
            type="stop"
          />
          <div>Stop Discovery</div>
        </button>
      </li>
      <li class="nav-item">
        <a class="item-link">
          <XNotificationPeek v-if="!isExpired" />
          <XIcon
            v-else
            family="navigation"
            type="notifications"
            :style="{fontSize: '20px', position: 'relative', top: '4px'}"
          />
        </a>
      </li>
      <li
        class="nav-item"
        :class="{ disabled: cannotViewSettings}"
      >
        <a
          id="settings"
          class="item-link"
          @click="navigateSettings"
        >
          <XIcon
            family="navigation"
            type="settings"
            :style="{fontSize: '20px', position: 'relative', top: '4px'}"
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
          content="In order to create a ServiceNow computer or incident
          , configure it under settings"
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
import _get from 'lodash/get';
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
      userPermissions(state) {
        const user = _get(state, 'auth.currentUser.data') || {};
        return user.permissions;
      },
    }),
    ...mapGetters({
      isExpired: IS_EXPIRED,
    }),
    cannotViewSettings() {
      return this.$cannot(
        this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.View,
      );
    },
    cannotRunDiscovery() {
      return this.$cannot(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.RunManualDiscovery);
    },
    anyEmptySettings() {
      return Object.values(this.emptySettings).find((value) => value);
    },
  },
  mounted() {
    const updateLifecycle = () => {
      this.fetchLifecycle().then(() => {
        // eslint-disable-next-line no-underscore-dangle
        if (this._isDestroyed) return;
        if (this.expired) return;
        if ((this.researchStatusLocal !== ''
                  && this.researchStatusLocal !== 'done'
                  && this.researchStatus === 'done')
            || (this.researchStatusLocal === '' && this.researchStatus === 'running')) {
          entities.forEach((entity) => {
            if (!this.$canViewEntity(entity.name)) return;
            this.fetchDataFields({ module: entity.name });
          });
        }
        this.researchStatusLocal = this.researchStatus;
        this.timer = setTimeout(updateLifecycle, 3000);
      });
    };
    if (!this.cannotRunDiscovery) {
      updateLifecycle();
    }
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
      this.researchStatusLocal = 'starting';
      // eslint-disable-next-line no-return-assign
      this.startResearch().catch(() => this.researchStatusLocal = '');
    },
    stopResearchNow() {
      this.researchStatusLocal = 'stopping';
      // eslint-disable-next-line no-return-assign
      this.stopResearch().catch(() => this.researchStatusLocal = 'running');
    },
    navigateSettings() {
      if (this.cannotViewSettings) {
        return;
      }
      if (this.anyEmptySettings) {
        this.$router.push({ path: '/settings#global-settings-tab' });
        this.dismissAllSettings();
      } else {
        this.$router.push({ name: 'Settings' });
      }
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
        settings: Object.keys(this.emptySettings)
          .reduce((map, setting) => ({ ...map, [setting]: false }), {}),
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
                cursor: pointer;
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
            display: flex;
            justify-content: center;
            align-items: center;
            .icon {
              font-size: 30px;
              padding: 4px;
            }
            .name {
              font-size: 100px;
            }
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
                position: relative;

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

                        .x-icon {
                          height: 22px;
                          font-size: 22px;
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
