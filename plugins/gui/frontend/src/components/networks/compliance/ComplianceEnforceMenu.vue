<template>
  <div>
    <ADropdown
      :trigger="enforcementRestricted?['']:['click']"
      placement="bottomRight"
      :disabled="enforcementRestricted"
      :visible="dropDownVisible"
      @visibleChange="openCloseMenu"
      overlayClassName="x-enforcement-menu"
    >
      <XButton
        @trigger="openCloseMenu"
        type="link"
        class="compliance-action-button"
      >
        <VIcon
          :disabled="enforcementRestricted"
          size="18"
        >$vuetify.icons.enforcementsDark</VIcon>
        <span class="enforce-title">Enforce</span>
      </XButton>
      <AMenu
        slot="overlay"
      >
        <AMenuItem
          id="cis_send_mail"
          key="cis_send_mail"
          @click="openEmailDialog()"
        >
          <div class="email-enforce-item">
            Send Email
          </div>
        </AMenuItem>
      </AMenu>
    </ADropdown>
    <XComplianceEmailDialog
      ref="emailDialog"
      :cis-name="cisName"
      :cis-title="cisTitle"
      :accounts="accounts"
      :module="module"
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
import XButton from '../../axons/inputs/Button.vue';
import XComplianceEmailDialog from './ComplianceEmailDialog.vue';
import configMixin from '../../../mixins/config';

export default {
  name: 'XEnforcementMenu',
  components: {
    XButton,
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
    XComplianceEmailDialog,
    XEnforcementsFeatureLockTip,
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
  },
  data() {
    return {
      dropDownVisible: false,
      showEmailDialog: false,
      actionToTip: null,
      displayFeatureLockTip: false,
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
      this.$refs.emailDialog.activate();
    },
    closeFeatureLockTip() {
      this.displayFeatureLockTip = false;
    },
  },
};
</script>

<style scoped lang="scss">
    .enforce-title {
        margin-left: 3px;
    }
    .email-enforce-item {
        display: flex;
        align-items: center;
        .md-image {
            height: 14px;
            margin-right: 5px;
        }
    }
</style>
