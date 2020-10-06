<template>
  <div class="x-vault-edit">
    <XStringEdit
      v-model="data"
      :schema="schema"
      :read-only="readOnly"
      @validate="onValidate"
      @input="input"
      @keydown="onKeyPress"
    >
      <template slot="icon">
        <AIcon
          v-if="loading"
          type="loading"
          class="provider-loading"
        />
        <div
          v-else
          :title="getTooltip"
          class="provider-toggle"
          @click="toggleQueryModal"
        >
          <XIcon
            v-if="vaultIcon"
            family="logo"
            :type="vaultIcon"
            class="provider-toggle__icon"
          />
          <XIcon
            v-if="vaultStatusIcon"
            theme="filled"
            :type="vaultStatusIcon"
            class="provider-toggle__status"
            :class="vaultStatusClass"
          />
        </div>
      </template>
    </XStringEdit>
    <AModal
      :visible="queryModal.open"
      class="vault-fetch w-md"
      :closable="false"
      :width="null"
      :centered="true"
      @cancel="toggleQueryModal"
    >
      <template #title>
        <div class="vault-fetch__title">
          <XIcon
            family="logo"
            :type="vaultIcon"
            :style="{fontSize: '24px'}"
          />
          {{ vaultProvider.title }}
        </div>
      </template>
      <XForm
        v-model="queryModal.data"
        :schema="vaultProvider.schema"
        @validate="updateFetchValidity"
      />
      <template #footer>
        <XButton
          type="link"
          @click="toggleQueryModal"
        >Cancel</XButton>
        <XButton
          type="primary"
          :disabled="!queryModal.valid"
          @click="testValueQuery"
        >Fetch</XButton>
      </template>
    </AModal>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import _get from 'lodash/get';
import _isEmpty from 'lodash/isEmpty';

import axiosClient from '@api/axios';
import { LOAD_PLUGIN_CONFIG } from '@store/modules/settings';
import { parseVaultError } from '@constants/utils';
import { vaultProviderEnum } from '@constants/settings';
import primitiveMixin from '@mixins/primitive';

import { Icon, Modal } from 'ant-design-vue';
import XForm from '@neurons/schema/Form.vue';
import XStringEdit from './StringEdit.vue';

export default {
  name: 'XVaultEdit',
  components: {
    XStringEdit, AIcon: Icon, AModal: Modal, XForm,
  },
  mixins: [primitiveMixin],
  data() {
    return {
      queryModal: {
        open: false,
        valid: false,
        data: {},
      },
      passString: '',
      error: '',
      success: false,
      loading: false,
    };
  },
  computed: {
    ...mapState({
      vaultProvider(state) {
        const providerName = _get(state, 'settings.configurable.core.CoreService.config.vault_settings.conditional', '');
        return providerName ? vaultProviderEnum[providerName] : {};
      },
    }),
    isNativePassword() {
      return Array.isArray(this.data) || typeof this.data === 'string';
    },
    getTooltip() {
      if (this.error) {
        return this.error;
      }
      if (this.success) {
        const fieldToTitledValue = (item) => `${item.title}: ${this.queryModal.data[item.name]}`;
        return this.vaultProvider.schema.items.map(fieldToTitledValue).join('\n');
      }
      return `Use ${this.vaultProvider.title}`;
    },
    vaultIcon() {
      return this.vaultProvider.name || '';
    },
    vaultStatusClass() {
      if (this.success) {
        return 'icon-success';
      }
      if (this.error) {
        return 'icon-error';
      }
      return '';
    },
    vaultStatusIcon() {
      if (this.success) {
        return 'check-circle';
      }
      if (this.error) {
        return 'close-circle';
      }
      return '';
    },
  },
  async created() {
    await this.loadPluginConfig({
      pluginId: 'core',
      configName: 'CoreService',
    });
  },
  mounted() {
    this.data = this.value;
    if (this.value && this.value.data) {
      this.queryModal.data = this.value.data;
      if (this.value.error) {
        this.error = this.value.error;
      } else {
        this.success = true;
      }
    }
  },
  methods: {
    ...mapActions({
      loadPluginConfig: LOAD_PLUGIN_CONFIG,
    }),
    toggleQueryModal() {
      this.queryModal.open = !this.queryModal.open;
    },
    testValueQuery() {
      this.toggleQueryModal();
      this.success = false;
      this.error = '';
      this.loading = true;
      this.validate();
      axiosClient.post('password_vault', {
        data: this.queryModal.data,
        field: this.schema.name,
        vault_type: 'vault_provider',
      }).then((testRes) => {
        if (!testRes) return;
        this.success = true;
        this.data = { data: this.queryModal.data, type: 'vault_provider' };
        this.input();
        this.validate();
      }).catch((recievedError) => {
        this.success = false;
        this.validate(true);
        this.error = parseVaultError(recievedError.response.data.message).error;
      }).finally(() => {
        this.loading = false;
      });
    },
    onValidate(validity) {
      this.$emit('validate', validity);
    },
    onKeyPress() {
      if (_isEmpty(this.queryModal.data)) {
        return;
      }
      this.queryModal.data = {};
      this.data = '';
      this.success = false;
      this.input();
    },
    checkData() {
      if (!this.schema.required) {
        return true;
      }
      return this.success || (this.isNativePassword && !_isEmpty(this.data));
    },
    updateFetchValidity(validity) {
      this.queryModal.valid = validity;
    },
  },
};
</script>

<style lang="scss">
  .x-vault-edit {
    .string-input-container {
      position: relative;

      .provider-toggle, .provider-loading {
        position: absolute;
        right: 4px;
        top: 0;
        height: 22px;
      }

      .provider-toggle {
        cursor: pointer;

        &__icon {
          font-size: 22px;
        }

        &__status {
          font-size: 10px;
          position: absolute;
          right: 0;
          bottom: 0;
          background-color: unset !important;
        }
      }

      .provider-loading {
        font-size: 22px;
      }
    }
  }

  .vault-fetch {
    &__title {
      font-size: 16px;
      display: flex;
      align-items: center;
    }

    .x-array-edit > div > div > .list {
      grid-template-columns: 1fr;
    }
  }
</style>
