<template>
  <header
    class="x-top-bar"
    :class="{ 'minimize': collapseSidebar }"
  >
    <div class="bar-toggle">
      <a
        class="toggle-link"
        @click="toggleSidebar"
      >
        <svg-icon
          name="navigation/menu"
          :original="true"
          height="20"
        />
      </a>
    </div>
    <div
      class="bar-logo"
    >
      <svg-icon
        name="logo/logo"
        height="30"
        :original="true"
      />
      <svg-icon
        name="logo/axonius"
        height="16"
        :original="true"
        class="logo-text"
      />
    </div>
    <x-trial-banner />
    <ul class="bar-nav">
      <li class="nav-item">
        <button
          v-if="researchStatusLocal === 'starting'"
          class="item-link research-link"
          disabled
        >
          <svg-icon
            name="symbol/running"
            class="rotating"
            :original="true"
            height="20"
          />
          <div>Initiating...</div>
        </button>
        <button
          v-else-if="researchStatusLocal === 'stopping'"
          class="item-link research-link"
          disabled
          @click="stopResearchNow"
        >
          <svg-icon
            name="symbol/running"
            class="rotating"
            :original="true"
            height="20"
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
          <svg-icon
            name="action/start"
            :original="true"
            height="20"
          />
          <div>Discover Now</div>
        </button>
        <button
          v-else-if="researchStatusLocal === 'running'"
          id="stop_research"
          class="item-link research-link"
          :disabled="!isDashboardWrite"
          @click="stopResearchNow"
        >
          <svg-icon
            name="action/stop"
            :original="true"
            height="20"
          />
          <div>Stop Discovery</div>
        </button>
      </li>
      <li class="nav-item">
        <a class="item-link">
          <x-notification-peek v-if="!isExpired" />
          <svg-icon
            v-else
            name="navigation/notifications"
            :original="true"
            height="20"></svg-icon>
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
          <svg-icon
            name="navigation/settings"
            :original="true"
            height="20"
          />
        </a>
        <x-tip-info
          v-if="isEmptySetting('mail')"
          content="In order to send alerts through mail, configure it under settings"
          @dismiss="dismissEmptySetting('mail')"
        />
        <x-tip-info
          v-if="isEmptySetting('syslog')"
          content="In order to send alerts through a syslog system, configure it under settings"
          @dismiss="dismissEmptySetting('syslog')"
        />
        <x-tip-info
          v-if="isEmptySetting('httpsLog')"
          content="In order to send alerts through an HTTPS log system, configure it under settings"
          @dismiss="dismissEmptySetting('httpsLog')"
        />
        <x-tip-info
          v-if="isEmptySetting('serviceNow')"
          content="In order to create a ServiceNow computer or incident, configure it under settings"
          @dismiss="dismissEmptySetting('serviceNow')"
        />
        <x-tip-info
          v-if="isEmptySetting('freshService')"
          content="In order to create a FreshService incident, configure it under settings"
          @dismiss="dismissEmptySetting('freshService')"
        />
        <x-tip-info
          v-if="isEmptySetting('jira')"
          content="In order to create a Jira incident, configure it under settings"
          @dismiss="dismissEmptySetting('jira')"
        />

      </li>
      <li class="nav-item">
        <a
          class="item-link"
          @click="startTourOnClick"
        >
          <svg-icon
            name="action/help"
            :original="true"
            height="20"
          />
        </a>
        <x-tip-info
          v-if="activateTourTip"
          content="You can always start the tour again here"
          @dismiss="activateTourTip = false"
        />
      </li>
    </ul>
  </header>
</template>

<script>
  import xNotificationPeek from '../NotificationsPeek.vue'
  import xTipInfo from '../onboard/TipInfo.vue'
  import xTrialBanner from '../onboard/TrialBanner.vue'

  import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
  import { FETCH_LIFECYCLE } from '../../../store/modules/dashboard'
  import { UPDATE_EMPTY_STATE, START_TOUR } from '../../../store/modules/onboarding'
  import {IS_EXPIRED} from '../../../store/getters'
  import { TOGGLE_SIDEBAR } from '../../../store/mutations'
  import { START_RESEARCH_PHASE, STOP_RESEARCH_PHASE, FETCH_DATA_FIELDS } from '../../../store/actions'
  import { entities } from '../../../constants/entities'

  export default {
    name: 'XTopBar',
    components: {
      xNotificationPeek, xTipInfo, xTrialBanner
    },
    data () {
      return {
        isDown: false,
        activateTourTip: false,
        researchStatusLocal: ''
      }
    },
    computed: {
      ...mapState({
        collapseSidebar (state) {
          return state.interaction.collapseSidebar
        },
        emptySettings (state) {
          return state.onboarding.emptyStates.settings
        },
        researchStatus (state) {
          return state.dashboard.lifecycle.data.status
        },
        tourActive (state) {
          return state.onboarding.tourStates.active
        },
        isSettingsRestricted (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Settings === 'Restricted'
        },
        isDashboardWrite (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Dashboard === 'ReadWrite' || user.admin
        },
        userPermissions (state) {
          return state.auth.currentUser.data.permissions
        }
      }),
      ...mapGetters({
        isExpired: IS_EXPIRED
      }),
      anyEmptySettings () {
        return Object.values(this.emptySettings).find(value => value)
      }
    },
    watch: {
      tourActive (isActiveNow) {
        if (!isActiveNow) {
          this.activateTourTip = true
        }
      }
    },
    mounted () {
      const updateLifecycle = () => {
        this.fetchLifecycle().then(() => {
          if (this._isDestroyed) return
          if (this.expired) return
          if ((this.researchStatusLocal !== '' &&
                  this.researchStatusLocal !== 'done' &&
                  this.researchStatus === 'done')
            || (this.researchStatusLocal === '' && this.researchStatus === 'running')) {
            entities.forEach(entity => {
              if (this.entityRestricted(entity.title)) return
              this.fetchDataFields({ module: entity.name })
            })
          }
          this.researchStatusLocal = this.researchStatus
          this.timer = setTimeout(updateLifecycle, 3000)
        })
      }
      updateLifecycle()
    },
    beforeDestroy () {
      clearTimeout(this.timer)
    },
    methods: {
      ...mapMutations({
        toggleSidebar: TOGGLE_SIDEBAR, updateEmptyState: UPDATE_EMPTY_STATE, initTourState: START_TOUR
      }),
      ...mapActions({
        fetchLifecycle: FETCH_LIFECYCLE,
        startResearch: START_RESEARCH_PHASE,
        stopResearch: STOP_RESEARCH_PHASE,
        fetchDataFields: FETCH_DATA_FIELDS

      }),
      startTourOnClick(){
        this.$ga.event('tour', 'start', '', 1)
        this.initTourState()
      },
      startResearchNow () {
        this.$ga.event('research', 'start-now', '', 1)
        this.researchStatusLocal = 'starting'
        this.startResearch().catch(() => this.researchStatusLocal = '')
      },
      stopResearchNow () {
        this.$ga.event('research', 'stop-now', '', 1)
        this.researchStatusLocal = 'stopping'
        this.stopResearch().catch(() => this.researchStatusLocal = 'running')
      },
      navigateSettings () {
        if (this.isSettingsRestricted) {
          this.$emit('access-violation', name)
          return
        }
        if (this.anyEmptySettings) {
          this.$router.push({ path: '/settings#global-settings-tab' })
          this.dismissAllSettings()
        } else {
          this.$router.push({ name: 'Settings' })
        }
      },
      entityRestricted (entity) {
        return this.userPermissions[entity] === 'Restricted'
      },
      isEmptySetting (name) {
        return this.emptySettings[name]
      },
      dismissEmptySetting (name) {
        this.updateEmptyState({
          settings: {
            [name]: false
          }
        })
      },
      dismissAllSettings () {
        this.updateEmptyState({
          settings: Object.keys(this.emptySettings).reduce((map, setting) => {
            map[setting] = false
            return map
          }, {})
        })
      }
    }
  }
</script>

<style lang="scss">
    .x-top-bar {
        background: $grey-0;
        position: fixed;
        top: 0;
        width: 100%;
        z-index: 101;
        display: flex;
        height: 60px;

        .bar-toggle {
            line-height: 60px;
            width: 240px;
            text-align: left;
            background-color: $theme-black;
            transition: all ease-in 0.2s;

            .toggle-link {
                padding: 0 18px;

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