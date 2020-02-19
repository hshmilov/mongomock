<template>
  <x-page
    title="Settings"
    class="x-settings"
  >
    <x-tabs
      ref="tabs"
    >
      <x-tab
        id="research-settings-tab"
        title="Lifecycle Settings"
        :selected="true"
      >
        <div class="tab-settings">
          <template v-if="schedulerSettings && schedulerSettings.schema">
            <x-form
              v-model="schedulerSettings.config"
              :schema="schedulerSettings.schema"
              :read-only="isReadOnly"
              api-upload="plugins/system_scheduler"
              @validate="updateSchedulerValidity"
              @select=""
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
          <template v-if="coreSettings && coreSettings.schema">
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
          <template v-if="guiSettings && guiSettings.schema">
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
          v-if="featureFlags && featureFlags.schema"
          v-model="featureFlags.config"
          :schema="featureFlags.schema"
          class="tab-settings"
          @save="saveFeatureFlags"
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
import { mapState, mapActions, mapMutations } from 'vuex';
import moment from 'moment';
import xPage from '../axons/layout/Page.vue';
import xTabs from '../axons/tabs/Tabs.vue';
import xTab from '../axons/tabs/Tab.vue';
import xButton from '../axons/inputs/Button.vue';
import xToast from '../axons/popover/Toast.vue';
import xForm from '../neurons/schema/Form.vue';
import xCustom from '../neurons/schema/Custom.vue';
import xUsersRoles from '../networks/config/UsersRoles.vue';
import xMaintenance from '../networks/config/Maintenance.vue';
import xFeatureFlags from '../networks/config/FeatureFlags.vue';

import { SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG, CHANGE_PLUGIN_CONFIG } from '../../store/modules/settings';
import { UPDATE_SYSTEM_CONFIG } from '../../store/mutations';
import { REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '../../store/actions';
import { GET_USER } from '../../store/modules/auth';

export default {
  name: 'XSettings',
  components: {
    xPage, xTabs, xTab, xButton, xToast, xForm, xCustom, xUsersRoles, xMaintenance, xFeatureFlags,
  },
  computed: {
    ...mapState({
      isReadOnly(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Settings === 'ReadOnly';
      },
      isS(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Settings === 'ReadOnly';
      },
      schedulerSettings(state) {
        if (!state.settings.configurable.system_scheduler) return undefined;
        return state.settings.configurable.system_scheduler.SystemSchedulerService;
      },
      coreSettings(state) {
        if (!state.settings.configurable.core) return undefined;
        return state.settings.configurable.core.CoreService;
      },
      guiSettings(state) {
        if (!state.settings.configurable.gui) return undefined;
        return state.settings.configurable.gui.GuiService;
      },
      featureFlags(state) {
        if (!state.settings.configurable.gui) return undefined;
        return state.settings.configurable.gui.FeatureFlags;
      },
      users(state) {
        return state.auth.allUsers.data;
      },
      isAdmin(state) {
        return state.auth.currentUser.data
            && (state.auth.currentUser.data.admin || state.auth.currentUser.data.role_name === 'Admin');
      },
      isAxonius(state) {
        return state.auth.currentUser.data.user_name === '_axonius';
      },
    }),
    validResearchRate() {
      if (!this.schedulerSettings.config) return 12;
      return this.validNumber(this.schedulerSettings.config.discovery_settings.system_research_rate);
    },
    validResearchDate() {
      return this.schedulerSettings.config.discovery_settings.system_research_date.system_research_date_recurrence >= 0;
    },
    isContionalDate() {
      return (this.schedulerSettings.config.discovery_settings.conditional === 'system_research_date');
    },
    isResearchDisabled() {
      if (this.schedulerSettings.config.discovery_settings.conditional === 'system_research_date') {
        return !this.schedulerComplete || this.isReadOnly || !this.validResearchDate;
      }
      return !this.schedulerComplete || !this.validResearchRate || this.isReadOnly;
    },
  },
  data() {
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
        last_name: '',
      },
      userToRemove: null,
    };
  },
  created() {
    this.loadPluginConfig({
      pluginId: 'gui',
      configName: 'GuiService',
    });
    this.loadPluginConfig({
      pluginId: 'core',
      configName: 'CoreService',
    });
    this.loadPluginConfig({
      pluginId: 'system_scheduler',
      configName: 'SystemSchedulerService',
    });
    this.fetchData({
      rule: 'metadata',
    }).then((response) => {
      if (response.status === 200) {
        this.systemInfo = response.data;
      }
    });
  },
  methods: {
    ...mapMutations({
      changePluginConfig: CHANGE_PLUGIN_CONFIG,
      updateSystemConfig: UPDATE_SYSTEM_CONFIG,
    }),
    ...mapActions({
      fetchData: REQUEST_API,
      startResearch: START_RESEARCH_PHASE,
      stopResearch: STOP_RESEARCH_PHASE,
      updatePluginConfig: SAVE_PLUGIN_CONFIG,
      loadPluginConfig: LOAD_PLUGIN_CONFIG,
      getUser: GET_USER,
    }),
    validNumber(value) {
      return !(value === undefined || isNaN(value) || value <= 0);
    },
    saveGlobalSettings() {
      this.updatePluginConfig({
        pluginId: 'core',
        configName: 'CoreService',
        config: this.coreSettings.config,
      }).then((response) => {
        this.createToast(response);
        this.updateSystemConfig({
          data: {
            global: {
              mail: this.coreSettings.config.email_settings.enabled,
              syslog: this.coreSettings.config.syslog_settings.enabled,
              gettingStartedEnabled: this.coreSettings.config.getting_started_checklist.enabled,
              vault_settings: this.coreSettings.config.vault_settings.enabled,
            },
          },
        });
      }).catch((error) => {
        if (error.response.status === 400) {
          this.message = error.response.data.message;
        }
      });
    },
    saveSchedulerSettings() {
      this.updatePluginConfig({
        pluginId: 'system_scheduler',
        configName: 'SystemSchedulerService',
        config: this.schedulerSettings.config,
      }).then((response) => {
        this.createToast(response);
      }).catch((error) => {
        if (error.response.status === 400) {
          this.message = error.response.data.message;
        }
      });
    },
    updateSchedulerValidity(valid) {
      this.schedulerComplete = valid;
    },
    updateCoreValidity(valid) {
      this.coreComplete = valid;
    },
    updateGuiValidity(valid) {
      this.guiComplete = valid;
    },
    saveGuiSettings() {
      this.updatePluginConfig({
        pluginId: 'gui',
        configName: 'GuiService',
        config: this.guiSettings.config,
      }).then((response) => {
        this.createToast(response);
        this.updateSystemConfig({
          data: {
            system: this.guiSettings.config.system_settings,
          },
        });
      }).then(() => {
        this.getUser();
      }).catch((error) => {
        if (error.response.status === 400) {
          this.message = error.response.data.message;
        }
      });
    },
    saveFeatureFlags() {
      this.updatePluginConfig({
        pluginId: 'gui',
        configName: 'FeatureFlags',
        config: this.featureFlags.config,
      }).then((response) => {
        this.createToast(response);
      }).catch((error) => {
        if (error.response.status === 400) {
          this.message = error.response.data.message;
        }
      });
    },
    createToast(response) {
      if (response.status === 200) {
        this.message = 'Saved Successfully.';
      } else {
        this.message = `Error: ${response.data.message}`;
      }
    },
    validateSendTime(isSendTimeValid) {
      const c = this.schedulerSettings.error;
      // .field === this.schedulerSettings.config.discovery_settings.system_research_date);
      if (!isSendTimeValid) {
        // Add error the the validity fields if the time is invalid
        this.validity.error = 'Send time is invalid';
        const sendTimePickerError = this.validity.fields.find(getTimePickerError);
        if (!sendTimePickerError) {
          if (!sendTimePickerError) {
            this.validity.fields.push({
              field: 'send_time',
              error: this.validity.error,
            });
          }
        } else {
          // If the send time is valid and there is an error than removed it
          const sendTimeError = this.validity.fields.find(getTimePickerError);
          if (sendTimeError) {
            this.validity.fields = this.validity.fields.filter((error) => error.field !== sendTimeError.field);
            if (this.validity.fields.length === 0) {
              this.validity.error = '';
            }
          }
        }
      }
    },
  },
};
</script>
<style lang="scss">

  div[role="menu"] {
    min-width: auto !important;
  }

  .x-settings {
    .x-tabs {
      max-width: 840px;

      ul {
        padding-left: 0;
      }

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

    .time-picker-text input {
      alignment: top;
      font-size: 14px;
      padding-left: 1px;
    }

    .time-picker-text label {
      alignment: top;
      font-size: 14px;
      padding-left: 1px;
    }

    span.server-time {
      padding-left: 15px;
    }

    .research-settings-tab .x-form .x-array-edit {
      grid-template-columns: 1fr;

      .v-text-field > .v-input__control > .v-input__slot:before {
        border-style: none;
        border-width: thin 0 0;
      }
      .v-text-field > .v-input__control > .v-input__slot:after {
        border-style: none;
        border-width: thin 0 0;
      }
      .v-text-field > .v-input__control > .v-input__slot:hover {
        border-style: none;
        border-width: thin 0 0;
      }

      .item .object.expand {
        label {
          display: block;
        }

        .time-picker-text, .x-dropdown, input {
          display: inline-block;
          width: 200px;
        }

        .v-text-field {
          padding-top: 0;
        }

        .v-text-field__details, .v-messages {
          min-height: 0;
        }
      }
    }
  }
</style>
<x></x>
