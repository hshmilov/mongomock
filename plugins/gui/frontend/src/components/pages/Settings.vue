<template>
  <x-page
    title="Settings"
    class="x-settings"
  >
    <x-tabs
      ref="tabs"
      @click="determineState"
      @updated="initTourState"
    >
      <x-tab
        id="research-settings-tab"
        title="Lifecycle Settings"
        :selected="true"
      >
        <div class="tab-settings">
          <template v-if="schedulerSettings">
            <x-form
              v-model="schedulerSettings.config"
              :schema="schedulerSettings.schema"
              :read-only="isReadOnly"
              api-upload="plugins/system_scheduler"
              @validate="updateSchedulerValidity"
            />
            <div class="place-right">
              <x-button
                id="research-settings-save"
                :disabled="isResearchDisabled"
                @click="saveSchedulerSettings"
              >Save</x-button>
            </div>
          </template>
        </div>
      </x-tab>
      <x-tab
        id="global-settings-tab"
        ref="global"
        title="Global Settings"
      >
        <div class="tab-settings">
          <template v-if="coreSettings">
            <x-form
              v-model="coreSettings.config"
              :schema="coreSettings.schema"
              :read-only="isReadOnly"
              api-upload="plugins/core"
              @validate="updateCoreValidity"
            />
            <div class="footer">
              <x-maintenance
                v-if="$refs.global && $refs.global.isActive"
                :read-only="isReadOnly"
              />
              <x-button
                id="global-settings-save"
                :disabled="!coreComplete || isReadOnly"
                @click="saveGlobalSettings"
              >Save</x-button>
            </div>
          </template>
        </div>
      </x-tab>
      <x-tab
        id="gui-settings-tab"
        title="GUI Settings"
      >
        <div class="tab-settings">
          <template v-if="guiSettings">
            <x-form
              v-model="guiSettings.config"
              :schema="guiSettings.schema"
              :read-only="isReadOnly"
              api-upload="plugins/gui"
              @validate="updateGuiValidity"
            />
            <div class="place-right">
              <x-button
                id="gui-settings-save"
                :disabled="!guiComplete || isReadOnly"
                @click="saveGuiSettings"
              >Save</x-button>
            </div>
          </template>
        </div>
      </x-tab>
      <x-tab
        v-if="isAxonius"
        id="feature-flags-tab"
        title="Feature flags"
      >
        <x-feature-flags
          v-if="featureFlags"
          v-model="featureFlags.config"
          :schema="featureFlags.schema"
          @save="saveFeatureFlags"
          class="tab-settings"
        />
      </x-tab>
      <x-tab
        v-if="isAdmin"
        id="user-settings-tab"
        title="Manage Users"
      >
        <x-users-roles
          :read-only="isReadOnly"
          @toast="message = $event"
        />
      </x-tab>
      <x-tab
        id="about-settings-tab"
        title="About"
      >
        <div class="tab-settings">
          <x-custom
            :data="systemInfo"
            :vertical="true"
          />
        </div>
      </x-tab>
    </x-tabs>
    <x-toast
      v-if="message"
      v-model="message"
    />
  </x-page>
</template>

<script>
  import xPage from '../axons/layout/Page.vue'
  import xTabs from '../axons/tabs/Tabs.vue'
  import xTab from '../axons/tabs/Tab.vue'
  import xButton from '../axons/inputs/Button.vue'
  import xToast from '../axons/popover/Toast.vue'
  import xForm from '../neurons/schema/Form.vue'
  import xCustom from '../neurons/schema/Custom.vue'
  import xUsersRoles from '../networks/config/UsersRoles.vue'
  import xMaintenance from '../networks/config/Maintenance.vue'
  import xFeatureFlags from '../networks/config/FeatureFlags.vue'

  import { mapState, mapActions, mapMutations } from 'vuex'
  import { SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG } from '../../store/modules/settings'
  import { UPDATE_SYSTEM_CONFIG } from '../../store/mutations'
  import { REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '../../store/actions'
  import { CHANGE_TOUR_STATE } from '../../store/modules/onboarding'

  export default {
    name: 'XSettings',
    components: {
      xPage, xTabs, xTab, xButton, xToast, xForm, xCustom, xUsersRoles, xMaintenance, xFeatureFlags
    },
    computed: {
      ...mapState({
        isReadOnly (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Settings === 'ReadOnly'
        },
        schedulerSettings (state) {
          if (!state.settings.configurable.system_scheduler) return null
          return state.settings.configurable.system_scheduler.SystemSchedulerService
        },
        coreSettings (state) {
          if (!state.settings.configurable.core) return null
          return state.settings.configurable.core.CoreService
        },
        guiSettings (state) {
          if (!state.settings.configurable.gui) return null
          return state.settings.configurable.gui.GuiService
        },
        featureFlags (state) {
          if (!state.settings.configurable.gui) return null
          return state.settings.configurable.gui.FeatureFlags
        },
        users (state) {
          return state.auth.allUsers.data
        },
        isAdmin (state) {
          return state.auth.currentUser.data &&
            (state.auth.currentUser.data.admin || state.auth.currentUser.data.role_name === 'Admin')
        },
        isAxonius (state) {
          return state.auth.currentUser.data.user_name === '_axonius'
        }
      }),
      validResearchRate () {
        if (!this.schedulerSettings.config) return 12
        return this.validNumber(this.schedulerSettings.config.discovery_settings.system_research_rate)
      },
      isResearchDisabled () {
        return !this.schedulerComplete || !this.validResearchRate || this.isReadOnly
      }
    },
    data () {
      return {
        coreComplete: true,
        guiComplete: true,
        schedulerComplete: true,
        message: '',
        systemInfo: {},
        createUserActive: false,
        userForm: {
          user_name: '',
          password: '',
          first_name: '',
          last_name: ''
        },
        userToRemove: null,
        delayInitTourState: false
      }
    },
    created () {
      this.loadPluginConfig({
        pluginId: 'gui',
        configName: 'GuiService'
      })
      this.loadPluginConfig({
        pluginId: 'core',
        configName: 'CoreService'
      })
      this.loadPluginConfig({
        pluginId: 'system_scheduler',
        configName: 'SystemSchedulerService'
      }).then(() => this.delayInitTourState = true)
      this.fetchData({
        rule: 'metadata'
      }).then((response) => {
        if (response.status === 200) {
          this.systemInfo = response.data
        }
      })
    },
    mounted () {
      if (this.$route.hash) {
        this.$refs.tabs.selectTab(this.$route.hash.slice(1))
      }
    },
    methods: {
      ...mapMutations({
        changePluginConfig: CHANGE_PLUGIN_CONFIG,
        updateSystemConfig: UPDATE_SYSTEM_CONFIG,
        changeState: CHANGE_TOUR_STATE
      }),
      ...mapActions({
        fetchData: REQUEST_API,
        startResearch: START_RESEARCH_PHASE, stopResearch: STOP_RESEARCH_PHASE,
        updatePluginConfig: SAVE_PLUGIN_CONFIG, loadPluginConfig: LOAD_PLUGIN_CONFIG
      }),
      initTourState() {
        if (!this.delayInitTourState) return

        this.changeState({ name: 'lifecycleRate' })
        this.delayInitTourState = false
      },
      validNumber (value) {
        return !(value === undefined || isNaN(value) || value <= 0)

      },
      saveGlobalSettings () {
        this.updatePluginConfig({
          pluginId: 'core',
          configName: 'CoreService',
          config: this.coreSettings.config
        }).then(response => {
          this.createToast(response)
          this.updateSystemConfig({
            data: {
              global: {
                mail: this.coreSettings.config.email_settings.enabled,
                syslog: this.coreSettings.config.syslog_settings.enabled
              }
            }
          })
        }).catch(error => {
          if (error.response.status === 400) {
            this.message = error.response.data.message
          }
        })
      },
      saveSchedulerSettings () {
        this.updatePluginConfig({
          pluginId: 'system_scheduler',
          configName: 'SystemSchedulerService',
          config: this.schedulerSettings.config
        }).then(response => {
          this.createToast(response)
        }).catch(error => {
          if (error.response.status === 400) {
            this.message = error.response.data.message
          }
        })
      },
      updateSchedulerValidity (valid) {
        this.schedulerComplete = valid
      },
      updateCoreValidity (valid) {
        this.coreComplete = valid
      },
      updateGuiValidity (valid) {
        this.guiComplete = valid
      },
      saveGuiSettings () {
        this.updatePluginConfig({
          pluginId: 'gui',
          configName: 'GuiService',
          config: this.guiSettings.config
        }).then(response => {
          this.createToast(response)
          this.updateSystemConfig({
            data: {
              system: this.guiSettings.config.system_settings
            }
          })
        })
      },
      saveFeatureFlags () {
        this.updatePluginConfig({
          pluginId: 'gui',
          configName: 'FeatureFlags',
          config: this.featureFlags.config
        }).then(response => {
          this.createToast(response)
        })
      },
      createToast (response) {
        if (response.status === 200) {
          this.message = 'Saved Successfully.'
        } else {
          this.message = 'Error: ' + response.data.message
        }
      },
      determineState (tabId) {
        this.changeState({ name: tabId })
      }
    }
  }
</script>

<style lang="scss">
    .x-settings {

        .x-tabs {
            max-width: 840px;

            .tab-settings .x-form .x-array-edit {
                grid-template-columns: 1fr;
            }
        }

        .global-settings-tab {
            .footer {
                display: flex;
                align-items: flex-start;

                .md-card {
                    width: 80%;
                    flex: 1 0 auto;
                }

                > .x-button {
                    margin-top: 4px;
                }
            }
        }

    }
</style>
