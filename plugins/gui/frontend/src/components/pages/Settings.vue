<template>
  <XPage
    title="Settings"
    class="x-settings"
  >
    <XTabs
      ref="tabs"
    >
      <XTab
        id="research-settings-tab"
        title="Lifecycle Settings"
        :selected="true"
      >
        <div class="tab-settings">
          <template v-if="schedulerSettings && schedulerSettings.schema">
            <XForm
              v-model="schedulerSettings.config"
              :schema="schedulerSettings.schema"
              :read-only="!canUpdateSettings"
              api-upload="settings/plugins/system_scheduler"
              @validate="updateSchedulerValidity"
            />

            <div class="place-left">
              <XButton
                id="research-settings-save"
                type="primary"
                :disabled="isResearchDisabled"
                @click="saveSchedulerSettings"
              >Save</XButton>
            </div>
          </template>
        </div>
      </XTab>
      <XTab
        id="global-settings-tab"
        ref="global"
        title="Global Settings"
      >
        <div class="tab-settings">
          <template v-if="coreSettings && coreSettings.schema">
            <XForm
              v-model="coreSettings.config"
              :schema="coreSettings.schema"
              :read-only="!canUpdateSettings"
              api-upload="settings/plugins/core"
              @validate="updateCoreValidity"
            />
            <div class="footer">
              <XMaintenance
                v-if="$refs.global && $refs.global.isActive"
                :read-only="!canUpdateSettings"
              />
              <XButton
                id="global-settings-save"
                type="primary"
                :disabled="!coreComplete || !canUpdateSettings || !validPasswordPolicy
                  || !validPasswordResetSettings || !validPasswordProtection"
                @click="saveGlobalSettings"
              >Save</XButton>
            </div>
          </template>
        </div>
      </XTab>
      <XTab
        id="gui-settings-tab"
        title="GUI Settings"
      >
        <div class="tab-settings">
          <template v-if="guiSettings && guiSettings.schema">
            <XForm
              v-model="guiSettings.config"
              :schema="guiSettings.schema"
              :read-only="!canUpdateSettings"
              api-upload="settings/plugins/gui"
              @validate="updateGuiValidity"
            />
            <div class="place-left">
              <XButton
                id="gui-settings-save"
                type="primary"
                :disabled="!guiComplete || !canUpdateSettings"
                @click="saveGuiSettings"
              >Save</XButton>
            </div>
          </template>
        </div>
      </XTab>
      <XTab
        v-if="canViewUsersAndRoles"
        id="identity-providers-tab"
        title="Identity Providers Settings"
      >
        <div class="tab-settings">
          <template v-if="identityProvidersSettings && identityProvidersSettings.schema">
            <XForm
              v-model="identityProvidersSettings.config"
              :schema="identityProvidersSettings.schema"
              :read-only="!canUpdateSettings"
              :error="identityProvidersError"
              api-upload="settings/plugins/IdentityProviders"
              @validate="updateIdentityProviders"
            />
            <div class="footer">
              <XMaintenance
                v-if="$refs.global && $refs.global.isActive"
                :read-only="!canUpdateSettings"
              />
              <XButton
                id="identity-providers-save"
                type="primary"
                :disabled="!identityProvidersComplete || !canUpdateSettings"
                @click="saveIdentityProviders"
              >Save</XButton>
            </div>
          </template>
        </div>
      </XTab>
      <XTab
        v-if="$isAxoniusUser()"
        id="feature-flags-tab"
        title="Feature flags"
      >
        <XFeatureFlags
          v-if="featureFlags && featureFlags.schema"
          v-model="featureFlags.config"
          :schema="featureFlags.schema"
          class="tab-settings"
          @save="saveFeatureFlags"
        />
      </XTab>
      <XTab
        v-if="canViewUsersAndRoles"
        id="user-settings-tab"
        title="Manage Users"
      >
        <XUsersManagement />
      </XTab>
      <XTab
        v-if="canViewUsersAndRoles"
        id="roles-settings-tab"
        title="Manage Roles"
      >
        <XRolesTable />
      </XTab>
      <XTab
        id="certificate-settings-tab"
        title="Certificate Settings"
      >
        <XCertificateSettings />
      </XTab>
      <XTab
        v-if="tunnelTabEnabled || $isAxoniusUser()"
        id="tunnel-tab"
        title="Tunnel Settings"
      >
        <XTunnel />
      </XTab>
      <XTab
        id="about-settings-tab"
        title="About"
      >
        <div class="tab-settings">
          <XCustom
            :data="systemInfo"
            :vertical="true"
          />
          <label
            v-if="newVersionAvailable"
            class="new-version-available"
          > <a href="mailto:support@axonius.com?subject=Request for upgrade">
           Contact us</a> to request an update.</label>
        </div>
      </XTab>
    </XTabs>
    <XToast
      v-if="message"
      v-model="message"
    />
  </XPage>
</template>

<script>
/* eslint-disable camelcase */

import { mapState, mapActions, mapMutations } from 'vuex';
import _cloneDeep from 'lodash/cloneDeep';
import _findIndex from 'lodash/findIndex';
import _get from 'lodash/get';

import { SAVE_PLUGIN_CONFIG, LOAD_PLUGIN_CONFIG } from '@store/modules/settings';
import { UPDATE_SYSTEM_CONFIG, SHOW_TOASTER_MESSAGE } from '@store/mutations';
import { REQUEST_API, START_RESEARCH_PHASE, STOP_RESEARCH_PHASE } from '@store/actions';
import { GET_USER } from '@store/modules/auth';

import XUsersManagement from '@networks/settings-tabs/users-management/index.vue';
import XRolesTable from '../networks/settings-tabs/roles-management/index.vue';
import XPage from '../axons/layout/Page.vue';
import XTabs from '../axons/tabs/Tabs.vue';
import XTab from '../axons/tabs/Tab.vue';
import XButton from '../axons/inputs/Button.vue';
import XToast from '../axons/popover/Toast.vue';
import XForm from '../neurons/schema/Form.vue';
import XCustom from '../neurons/schema/Custom.vue';
import XMaintenance from '../networks/config/Maintenance.vue';
import XFeatureFlags from '../networks/config/FeatureFlags.vue';
import XTunnel from '../networks/config/Tunnel.vue';
import XCertificateSettings from '../networks/config/CertificateSettings.vue';
import {validateEmail} from "@constants/validations";

export default {
  name: 'XSettings',
  components: {
    XPage,
    XTabs,
    XTab,
    XButton,
    XToast,
    XForm,
    XCustom,
    XMaintenance,
    XFeatureFlags,
    XTunnel,
    XCertificateSettings,
    XUsersManagement,
    XRolesTable,
  },
  data() {
    return {
      schedulerSettings: {},
      coreSettings: {},
      guiSettings: {},
      featureFlags: {},
      identityProvidersSettings: {},
      identityProvidersError: '',
      coreComplete: true,
      guiComplete: true,
      identityProvidersComplete: true,
      schedulerComplete: true,
      message: '',
      systemInfo: {},
      newVersionAvailable: false,
    };
  },
  computed: {
    ...mapState({
      schedulerSettingsFromState(state) {
        if (!state.settings.configurable.system_scheduler) return undefined;
        return state.settings.configurable.system_scheduler.SystemSchedulerService;
      },
      coreSettingsFromState(state) {
        if (!state.settings.configurable.core) return undefined;
        return state.settings.configurable.core.CoreService;
      },
      guiSettingsFromState(state) {
        if (!state.settings.configurable.gui) return undefined;
        return state.settings.configurable.gui.GuiService;
      },
      featureFlagsFromState(state) {
        if (!state.settings.configurable.gui) return undefined;
        return state.settings.configurable.gui.FeatureFlags;
      },
      identityProvidersFromState(state) {
        if (!state.settings.configurable.gui) return undefined;
        return state.settings.configurable.gui.IdentityProviders;
      },
      users(state) {
        return state.auth.allUsers.data;
      },
    }),
    tunnelTabEnabled() {
      if (this.featureFlagsFromState.config !== undefined) {
        return this.featureFlagsFromState.config.enable_saas;
      }
      return true;
    },
    canUpdateSettings() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update);
    },
    validResearchRate() {
      if (!this.schedulerSettings.config) return 12;
      return this.validNumber(
        this.schedulerSettings.config.discovery_settings.system_research_rate,
      );
    },
    validResearchDate() {
      return this.schedulerSettings.config.discovery_settings
        .system_research_date.system_research_date_recurrence >= 0;
    },
    validPasswordResetSettings() {
      if (!this.coreSettings.config) {
        return false;
      }
      return this.validNumber(
        this.coreSettings.config.password_reset_password.reset_password_link_expiration,
      );
    },
    validPasswordPolicy() {
      if (!this.coreSettings.config) {
        return false;
      }
      if (!this.coreSettings.config.password_policy_settings.enabled) {
        return true;
      }

      const {
        password_min_lowercase, password_min_numbers,
        password_min_special_chars, password_min_uppercase, password_length,
      } = this.coreSettings.config.password_policy_settings;
      const sumChars = password_min_lowercase + password_min_numbers
        + password_min_special_chars + password_min_uppercase;

      return password_length > 0
      && password_min_lowercase >= 0
      && password_min_numbers >= 0
      && password_min_special_chars >= 0
      && password_min_uppercase >= 0
      && sumChars <= password_length;
    },
    validPasswordProtection() {
      if (!this.coreSettings.config) {
        return false;
      }
      if (!this.coreSettings.config.password_brute_force_protection.enabled) {
        return true;
      }

      const { password_max_allowed_tries, password_lockout_minutes } = this.coreSettings
        .config.password_brute_force_protection;

      return password_max_allowed_tries >= 5 && password_lockout_minutes > 0;
    },
    isResearchDisabled() {
      if (this.schedulerSettings.config.discovery_settings.conditional === 'system_research_date') {
        return !this.schedulerComplete || !this.canUpdateSettings || !this.validResearchDate;
      }
      return !this.schedulerComplete || !this.canUpdateSettings || !this.validResearchRate;
    },
    canViewUsersAndRoles() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.GetUsersAndRoles);
    },
    canEditRoles() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update, this.$permissionConsts.categories.Roles);
    },
  },
  async created() {
    await this.loadPluginConfig({
      pluginId: 'gui',
      configName: 'GuiService',
    });
    await this.loadPluginConfig({
      pluginId: 'core',
      configName: 'CoreService',
    });
    await this.loadPluginConfig({
      pluginId: 'system_scheduler',
      configName: 'SystemSchedulerService',
    });
    if (this.canViewUsersAndRoles) {
      await this.loadPluginConfig({
        pluginId: 'gui',
        configName: 'IdentityProviders',
      });
    }
    this.schedulerSettings = _cloneDeep(this.schedulerSettingsFromState);
    this.coreSettings = _cloneDeep(this.coreSettingsFromState);
    this.guiSettings = _cloneDeep(this.guiSettingsFromState);
    this.identityProvidersSettings = _cloneDeep(this.identityProvidersFromState);
    if (!this.canViewUsersAndRoles && !this.canEditRoles) {
      this.guiSettings.schema.items.forEach((serviceItem) => {
        const defaultRoleIdIndex = _findIndex(serviceItem.items, ((settingsItem) => settingsItem.name === 'default_role_id'));
        if (defaultRoleIdIndex > -1) {
          serviceItem.items.splice(defaultRoleIdIndex, 1);
        }
      });
    }
    this.featureFlags = _cloneDeep(this.featureFlagsFromState);
    const response = await this.fetchData({
      rule: 'settings/metadata',
    });
    this.systemInfo = response.data;
    this.newVersionAvailable = 'Latest Available Version' in this.systemInfo;
  },
  methods: {
    ...mapMutations({
      updateSystemConfig: UPDATE_SYSTEM_CONFIG,
      showToasterMessage: SHOW_TOASTER_MESSAGE,
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
      // eslint-disable-next-line no-restricted-globals
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
              passwordManagerEnabled: this.coreSettings.config.vault_settings.enabled,
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
        this.updateSystemConfig({
          data: {
            global: {
              historyEnabled: _get(this.schedulerSettings, 'config.discovery_settings.save_history', false),
            },
          },
        });
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
    updateIdentityProviders(valid) {
      let rulesValid = true;
      if (valid) {
        const ldapConfig = this.identityProvidersSettings.config.ldap_login_settings;
        if (ldapConfig.enabled) {
          const rulesHash = {};
          ldapConfig.role_assignment_rules.rules.forEach((rule) => {
            if (!rulesValid) {
              return;
            }
            if (rule.type === 'Email address') {
              if (!validateEmail(rule.value)) {
                this.identityProvidersError = 'LDAP assignment rule - invalid email address';
                rulesValid = false;
                return;
              }
            }
            const ruleHash = `${rule.type}_${rule.value}`;
            if (!rulesHash[ruleHash]) {
              rulesHash[ruleHash] = true;
            } else {
              this.identityProvidersError = 'Duplicated LDAP assignment rule';
              rulesValid = false;
            }
          });
        }

        const samlConfig = this.identityProvidersSettings.config.saml_login_settings;
        if (samlConfig.enabled) {
          const rulesHash = {};
          samlConfig.role_assignment_rules.rules.forEach((rule) => {
            const ruleHash = `${rule.key}_${rule.value}`;
            if (!rulesHash[ruleHash]) {
              rulesHash[ruleHash] = true;
            } else {
              this.identityProvidersError = 'Duplicated SAML assignment rule';
              rulesValid = false;
            }
          });
        }
      }
      if (rulesValid) {
        this.identityProvidersError = '';
      }
      this.identityProvidersComplete = valid && rulesValid;
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
        schema: this.featureFlags.schema,
      }).then((response) => {
        this.createToast(response);
      }).catch((error) => {
        if (error.response.status === 400) {
          this.message = error.response.data.message;
        }
      });
    },
    saveIdentityProviders() {
      this.updatePluginConfig({
        pluginId: 'gui',
        configName: 'IdentityProviders',
        config: this.identityProvidersSettings.config,
        schema: this.identityProvidersSettings.schema,
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
        this.message = 'Saved Successfully';
      } else {
        this.message = `Error: ${response.data.message}`;
      }
    },
  },
};
</script>
<style lang="scss">

  .x-settings {
    .x-tabs {
      height: calc(100% - 12px);

      .research-settings-tab,
      .global-settings-tab,
      .gui-settings-tab,
      .identity-providers-tab,
      .about-settings-tab {
        .x-form {
          max-width: 30%;
        }
      }

      .tab-settings .x-form .x-array-edit .list{
        grid-template-columns: 1fr;
      }
    }

    .global-settings-tab {
      .footer {
        display: flex;
        flex-direction: column;
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

    .research-settings-tab .x-form .x-array-edit .list {
      grid-template-columns: 1fr;

      .item_system_research_date_recurrence, .item_system_research_rate {
        input {
          width: 200px;
        }
      }
    }

    .identity-providers-tab {
      .draggable {
        min-width: 685px;
      }
      #role_assignment_rules {
        font-size: 16px;
        margin-top: 8px;
       }
      #rules {
        font-weight: unset;
        font-size: 14px;
        margin-top: 0;
      }
      .item_rules {
        min-width: 685px;
      }
      .x-array-edit {
        .list.draggable {
          .remove-button {
            padding-right: 0;
          }

          .list {
            .item_value {
              width: 300px;
            }
          }
        }
      }
    }
  }
</style>
