<template>
  <div class="x-adapter-client-connection">
    <div
      v-if="value.error"
      class="server-error"
    >
      <XIcon
        family="symbol"
        type="error"
      />
      <div class="error-text">
        {{ value.error }}
      </div>
    </div>
    <XForm
      v-model="value.serverData.client_config"
      :schema="adapterSchema"
      :api-upload="uploadFileEndpoint"
      :error="error"
      :passwords-vault-enabled="isPasswordVaultEnabled"
      @submit="$emit('save')"
      @validate="validateServer"
    />
    <div class="double-column">
      <div>
        <label for="connectionLabel">
          Connection Label
          <div
            v-if="!requireConnectionLabel"
            class="hint"
          >optional</div>
        </label>
        <input
          id="connectionLabel"
          v-model="value.connectionLabel"
          type="text"
          :class="{ 'error-border': showConnectionLabelBorder }"
          :maxlength="50"
          @input="onConnectionLabelInput"
          @blur="onConnectionLabelBlur"
        >
      </div>
      <XInstancesSelect
        id="serverInstance"
        v-model="value.instanceId"
        :render-label="true"
        render-label-text="Choose Instance"
        :hide-in-one-option="true"
      />
    </div>
  </div>
</template>

<script>
import { mapState } from 'vuex';
import _get from 'lodash/get';
import { XInstancesSelect } from '@axons/inputs/dynamicSelects';
import XForm from '@neurons/schema/Form.vue';
import XIcon from '@axons/icons/Icon';

export default {
  name: 'XAdapterClientConnection',
  components: {
    XInstancesSelect,
    XForm,
    XIcon,
  },
  props: {
    value: {
      type: Object,
      default: () => {},
    },
    adapterId: {
      type: String,
      default: null,
    },
    adapterSchema: {
      type: Object,
      default: () => {},
    },
    error: {
      type: String,
      default: '',
    },
    requireConnectionLabel: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    ...mapState({
      isPasswordVaultEnabled(state) {
        return _get(state, 'configuration.data.global.passwordManagerEnabled', false);
      },
    }),
    uploadFileEndpoint() {
      return `adapters/${this.adapterId}/${this.value.instanceId}`;
    },
  },
  data() {
    return {
      showConnectionLabelBorder: false,
    };
  },
  methods: {
    onConnectionLabelInput() {
      if (this.requireConnectionLabel && this.value.connectionLabel) {
        this.showConnectionLabelBorder = false;
        this.$emit('error-update', '');
      }
    },
    onConnectionLabelBlur() {
      this.showConnectionLabelBorder = !this.connectionLabelValid;
      this.$emit('error-update', this.connectionLabelValid ? '' : 'Connection Label is required');
    },
    validateServer(valid) {
      this.$emit('validate', valid);
      if (!valid) {
        this.$emit('error-update', '');
      }
    },
  },
};
</script>

<style scoped>

</style>
