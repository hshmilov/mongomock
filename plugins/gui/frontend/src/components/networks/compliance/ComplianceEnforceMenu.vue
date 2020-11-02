<template>
  <div>
    <ADropdown
      :trigger="enforcementRestricted?['']:['click']"
      placement="bottomRight"
      :disabled="enforcementRestricted || disabled"
      :visible="dropDownVisible"
      overlay-class-name="x-enforcement-menu"
      @visibleChange="openCloseMenu"
    >
      <XButton
        type="link"
        class="compliance-action-button"
        @trigger="openCloseMenu"
      >
        <XIcon
          family="symbol"
          type="enforcements"
          class="standard-icon"
          :class="{'disabled-icon': enforcementRestricted || disabled}"
        />
        <span class="enforce-title">Enforce</span>
      </XButton>
      <AMenu
        slot="overlay"
      >
        <AMenuItem
          id="cis_send_mail"
          key="cis_send_mail"
          @click="openEmailDialog"
        >
          <div class="enforce-item">
            Send Email
          </div>
        </AMenuItem>
        <AMenuItem
          id="cis_jira_action"
          key="cis_jira_action"
          @click="openJiraDialog"
        >
          <div class="enforce-item">
            Create Jira Issue
          </div>
        </AMenuItem>
      </AMenu>
    </ADropdown>
    <XComplianceEmailDialog
      v-if="!enforcementRestricted"
      ref="emailDialog"
      :cis-name="cisName"
      :cis-title="cisTitle"
      :accounts="accounts"
      :module="module"
      :rules="rules"
      :categories="categories"
      :failed-only="failedOnly"
      :is-active="emailActive"
      :aggregated-view="aggregatedView"
      @close="closeEmailDialog"
    />
    <XComplianceJiraDialog
      v-if="!enforcementRestricted"
      ref="jiraDialog"
      :cis-name="cisName"
      :cis-title="cisTitle"
      :accounts="accounts"
      :module="module"
      :rules="rules"
      :categories="categories"
      :failed-only="failedOnly"
      :is-active="jiraActive"
      :aggregated-view="aggregatedView"
      @close="closeJiraDialog"
    />
    <XEnforcementsFeatureLockTip
      :enabled="displayFeatureLockTip"
      @close-lock-tip="closeFeatureLockTip"
    />
  </div>
</template>

<script>
import {
  Dropdown, Menu,
} from 'ant-design-vue';
import { mapState } from 'vuex';
import _get from 'lodash/get';
import XEnforcementsFeatureLockTip from '@networks/enforcement/EnforcementsFeatureLockTip.vue';
import XComplianceEmailDialog from './ComplianceEmailDialog.vue';
import XComplianceJiraDialog from './ComplianceJiraDialog.vue';
import configMixin from '../../../mixins/config';

export default {
  name: 'XEnforcementMenu',
  components: {
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
    XComplianceEmailDialog,
    XEnforcementsFeatureLockTip,
    XComplianceJiraDialog,
  },
  mixins: [configMixin],
  props: {
    cisName: {
      type: String,
      default: '',
    },
    cisTitle: {
      type: String,
      default: '',
    },
    accounts: {
      type: Array,
      default: () => [],
    },
    module: {
      type: String,
      default: '',
    },
    rules: {
      type: Array,
      default: () => [],
    },
    categories: {
      type: Array,
      default: () => [],
    },
    failedOnly: {
      type: Boolean,
      default: false,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    aggregatedView: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      dropDownVisible: false,
      showEmailDialog: false,
      actionToTip: null,
      displayFeatureLockTip: false,
      jiraActive: false,
      emailActive: false,
    };
  },
  computed: {
    ...mapState({
      enforcementsLocked(state) {
        return !_get(state, 'settings.configurable.gui.FeatureFlags.config.enforcement_center', true);
      },
    }),
    mailActionName() {
      return this.settingToActions.mail[0];
    },
    jiraActionName() {
      return this.settingToActions.jira[0];
    },
    enforcementRestricted() {
      return this.$cannot(this.$permissionConsts.categories.Enforcements,
        this.$permissionConsts.actions.Add);
    },
  },
  methods: {
    openCloseMenu() {
      if (this.enforcementsLocked) {
        this.displayFeatureLockTip = true;
        return;
      }
      this.dropDownVisible = !this.dropDownVisible;
    },
    openEmailDialog() {
      this.dropDownVisible = false;
      this.checkEmptySettings(this.mailActionName);
      if (this.anyEmptySettings) {
        return;
      }
      this.emailActive = true;
    },
    openJiraDialog() {
      this.dropDownVisible = false;
      this.checkEmptySettings(this.jiraActionName);
      if (this.anyEmptySettings) {
        return;
      }
      this.jiraActive = true;
    },
    closeFeatureLockTip() {
      this.displayFeatureLockTip = false;
    },
    closeJiraDialog() {
      this.jiraActive = false;
    },
    closeEmailDialog() {
      this.emailActive = false;
    },
  },
};
</script>

<style scoped lang="scss">
    XIcon {
      color: red;
    }

    .enforce-title {
        margin-left: 3px;
    }
    .enforce-item {
        display: flex;
        align-items: center;
        .md-image {
            height: 14px;
            margin-right: 5px;
        }
    }
</style>
