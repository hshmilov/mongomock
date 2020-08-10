<template>
  <ADropdown
    :trigger="['click']"
    placement="bottomRight"
  >
    <XButton
      class="actions-toggle"
    >
      <XIcon
        type="thunderbolt"
      />
      Certificate Actions</XButton>
    <AMenu
      slot="overlay"
    >
      <AMenuItem
        id="generate_csr"
        key="0"
        @click="generateCSR"
      >
        Generate CSR
      </AMenuItem>
      <AMenuItem
        id="import_cert_and_key"
        key="1"
        @click="importCertAndKey"
      >
        Import Certificate and Private Key
      </AMenuItem>
      <AMenuItem
        id="import_csr"
        key="2"
        :disabled="!isActiveCSR"
        @click="importCSR"
      >
        Import Signed Certificate (CSR)
      </AMenuItem>
      <AMenuItem
        id="reset_to_defaults"
        key="3"
        @click="resetToDefaults"
      >
        Restore to System Default
      </AMenuItem>
    </AMenu>
  </ADropdown>
</template>

<script>
import { mapState } from 'vuex';
import _get from 'lodash/get';
import { Dropdown, Menu } from 'ant-design-vue';
import XIcon from '@axons/icons/Icon';
import XButton from '@axons/inputs/Button.vue';
import {
  generateCSRAction, importCertAndKeyAction, importCSRAction, resetSystemDefaultsAction,
} from '../../../constants/settings';

export default {
  name: 'XCertificateActions',
  components: {
    XButton,
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
    XIcon,
  },
  computed: {
    ...mapState({
      isActiveCSR(state) {
        return _get(state, 'settings.configurable.core.CoreService.config.csr_settings.status');
      },
    }),
  },
  methods: {
    generateCSR() {
      this.$emit('action', generateCSRAction);
    },
    importCertAndKey() {
      this.$emit('action', importCertAndKeyAction);
    },
    importCSR() {
      this.$emit('action', importCSRAction);
    },
    resetToDefaults() {
      this.$emit('action', resetSystemDefaultsAction);
    },
  },
};

</script>
<style lang="scss">
  .actions-toggle {
    position: absolute;
    right: 2em;
    top: 5em;
  }
</style>
