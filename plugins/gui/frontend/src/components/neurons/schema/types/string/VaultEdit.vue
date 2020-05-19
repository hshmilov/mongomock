<template>
  <div>
    <string
      v-model="processedData"
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
        />
        <div
          v-else
          :title="getTooltip"
          class="provider-toggle"
        >
          <VIcon
            @click.native="toggleQueryModal"
          >{{ `$${vaultStatusIcon}` }}</VIcon>
        </div>
      </template>
    </string>
    <XModal
      v-if="queryModal.open"
      approve-text="Fetch"
      size="md"
      :disabled="!queryModal.valid"
      @close="toggleQueryModal"
      @confirm="testValueQuery"
    >

      <div slot="body">
        <div class="vault-header">
          <VIcon>{{ `$${vaultIcon}` }}</VIcon>{{ vaultProvider.title }}
        </div>
        <label for="provider-input">{{ vaultProvider.schema.title }}:</label>
        <Component
          :is="vaultProvider.schema.type"
          id="provider-input"
          v-model="queryModal.current_query"
          :schema="vaultProvider.schema"
          @validate="updateFetchValidity"
        />
      </div>
    </XModal>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import _get from 'lodash/get';

import axiosClient from '@api/axios';
import { LOAD_PLUGIN_CONFIG } from '@store/modules/settings';
import { parseVaultError } from '@constants/utils';
import { vaultProviderEnum } from '@constants/settings';
import primitiveMixin from '@mixins/primitive';

import { Icon } from 'ant-design-vue';
import XModal from '@axons/popover/Modal/index.vue';
import string from './StringEdit.vue';
import integer from '../numerical/IntegerEdit.vue';

export default {
  name: 'XVaultEdit',
  components: {
    XModal, AIcon: Icon, string, integer,
  },
  mixins: [primitiveMixin],
  data() {
    return {
      queryModal: {
        open: false,
        valid: false,
        current_query: '',
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
    processedData: {
      get() {
        return this.isUnchangedPassword ? '********' : this.data;
      },
      set(value) {
        this.data = value;
      },
    },
    getTooltip() {
      if (this.error) {
        return this.error;
      }
      if (this.success) {
        return `${this.vaultProvider.schema.title}: ${this.queryModal.current_query}`;
      }
      return `Use ${this.vaultProvider.title}`;
    },
    isUnchangedPassword() {
      return this.inputType === 'password' && this.data && this.data[0] === 'unchanged';
    },
    vaultIcon() {
      return this.vaultProvider.name;
    },
    vaultStatusIcon() {
      let statusPostfix = '';
      if (this.success) {
        statusPostfix = 'Success';
      }
      if (this.error) {
        statusPostfix = 'Error';
      }
      return `${this.vaultIcon}${statusPostfix}`;
    },
  },
  async created() {
    await this.loadPluginConfig({
      pluginId: 'core',
      configName: 'CoreService',
    });
  },
  mounted() {
    if (this.value && this.value.query) {
      this.data = this.value;
      this.queryModal.current_query = this.data.query;
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
        query: this.queryModal.current_query,
        field: this.schema.name,
        vault_type: 'vault_provider',
      }).then((testRes) => {
        if (!testRes) return;
        this.success = true;
        this.data = { query: this.queryModal.current_query, type: 'vault_provider' };
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
      if (!this.queryModal.current_query) return;
      this.queryModal.current_query = '';
      this.data = '';
      this.success = false;
      this.input();
    },
    checkData() {
      return this.success || !this.schema.required;
    },
    updateFetchValidity(validity) {
      this.queryModal.valid = validity.valid;
    },
  },
};
</script>

<style lang="scss">

    .string-input-container {
        position: relative;

        .provider-toggle {
            position: absolute;
            right: 4px;
            cursor: pointer;
            top: 0;
        }
        .anticon {
            border: 0;
            position: absolute;
            right: 8px;
            top: 2px;
            line-height: 24px;
            cursor: pointer;
        }
    }

    .vault-header {
      margin-bottom: 8px;

      .v-icon {
        height: 36px;
        width: 32px;
      }
    }

    #provider-input {
        resize: none;
    }
</style>
