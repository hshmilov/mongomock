<template>
  <XModal
    approve-text="Import"
    :disabled="!formValid"
    @confirm="importCertificate"
    @close="cancelImportCertAndKey"
  >
    <div slot="body">
      <div>
        <div class="content">
          <h2>Import Certificate and Private Key</h2>
          <XForm
            v-model="globalSSL"
            :schema="importCertAndKeySchema"
            api-upload="settings/plugins/core"
            silent
            @validate="onFormValidate"
          />
        </div>
      </div>
    </div>
  </XModal>
</template>

<script>
import { mapActions, mapState } from 'vuex';
import XForm from '../../neurons/schema/Form.vue';
import XModal from '../../axons/popover/Modal/index.vue';
import { SET_GLOBAL_SSL_SETTINGS } from '../../../store/modules/settings';

export default {
  name: 'XImportCertAndKeyModal',
  components: { XModal, XForm },
  data() {
    return {
      formValid: false,
      globalSSL: {
        enabled: true,
        hostname: '',
        cert_file: null,
        private_key: null,
        passphrase: '',
      },
    };
  },
  computed: {
    ...mapState({
      globalSSLSettings(state) {
        return state.settings.configurable.core.CoreService.config.global_ssl;
      },
      globalSSLItems(state){
        return state.settings.configurable.core.CoreService.schema.items.find((item) => item.name == 'global_ssl').items;
      },
      globalSSLRequiredItems(state){
        return state.settings.configurable.core.CoreService.schema.items.find((item) => item.name == 'global_ssl').required;
      },
    }),
    importCertAndKeySchema() {
      return {
        type: 'array',
        required: this.globalSSLRequiredItems,
        items: this.globalSSLItems,
      };
    },
  },
  mounted() {
    this.globalSSL = this.globalSSLSettings;
    this.globalSSL.enabled = true;
  },
  methods: {
    ...mapActions({
      setGlobalSSLSettings: SET_GLOBAL_SSL_SETTINGS,
    }),
    importCertificate() {
      this.setGlobalSSLSettings(this.globalSSL).then(() => {
        this.$emit('toaster', 'Certificate imported successfully');
        this.$emit('refresh');
      }).catch((error) => {
        this.$emit('toaster', error.response.data.message);
      }).then(() => {
        this.$emit('closed');
      });
    },
    cancelImportCertAndKey() {
      this.$emit('closed');
    },
    onFormValidate(valid) {
      this.formValid = valid;
    },
  },
};

</script>

<style lang="scss">
  .x-array-edit {
    display: block !important;
  }
</style>
