<template>
  <div
    class="x-certificate-settings"
  >
    <h1 class="header">
      SSL Certificate
    </h1>
    <XCertificateActions
      :disabled="!canUpdateSettings"
      @refresh="refreshSettings"
      @action="actionToggle"
      @toaster="setTostaterMsg"
    />
    <XImportCertAndKeyModal
      v-if="importCertAndKeyActive"
      @closed="actionToggle('importCertAndKey')"
      @refresh="refreshSettings"
      @toaster="setTostaterMsg"
    />
    <XInstallCSRModal
      v-if="importCsrActive"
      @closed="actionToggle('importCSR')"
      @refresh="refreshSettings"
      @toaster="setTostaterMsg"
    />
    <XCreateCSRModal
      v-if="generateCsrActive"
      @closed="actionToggle('generateCSR')"
      @refresh="refreshSettings"
      @toaster="setTostaterMsg"
    />
    <XModal
      v-if="resetSystemDefaultsActive"
      approve-text="Restore To Default"
      @confirm="resetToDefaults"
      @close="actionToggle('resetSystemDefaults')"
    >
      <div slot="body">
        <div>This certificate settings will be reset to default.</div>
        <div>The default Axonius self-signed certificate will be used.</div>
        <div>Do you want to continue?</div>
      </div>
    </XModal>
    <h5 class="header header-title">
      Issued to:
    </h5>
    <p class="header header-text">
      {{ issuedTo }}
    </p>
    <div v-if="alternativeNames != ''">
      <h5 class="header header-title">
        Alternative names:
      </h5>
      <p class="header header-text">
        {{ alternativeNames }}
      </p>
    </div>
    <h5 class="header header-title">
      Issued by:
    </h5>
    <p class="header header-text">
      {{ issuedBy }}
    </p>
    <h5 class="header header-title">
      SHA1 fingerprint:
    </h5>
    <p class="header header-text">
      {{ sha1Fingerprint }}
    </p>
    <h5 class="header header-title">
      Expires on:
    </h5>
    <p class="header header-text">
      {{ expiresOn }}
    </p>
    <h1 class="header">
      Certificate Signing Request (CSR)
    </h1>
    <div v-if="isActiveCSR">
      <h5 class="header header-title">
        CSR pending for:
      </h5>
      <p class="header header-text">
        {{ csrPendingName }}
      </p>
      <h5 class="header header-title">
        Pending since:
      </h5>
      <p class="header header-text">
        {{ csrPendingSince }}
      </p>
      <XButton
        type="link"
        style="margin-left: -1em;"
        @click="cancelCSR"
      >Cancel Pending Request</XButton>
      <XButton
          id="csr_download"
          type="primary"
          :loading="downloading"
          @click="startDownload"
      >
        {{ downloading ? 'Downloading': 'Download CSR' }}
      </XButton>
      <div>&nbsp;</div>
    </div>
    <div v-else>
      <p>None</p>
    </div>
    <hr>
    <XForm
      v-model="SSLTrust"
      :schema="sslTrustSchema"
      api-upload="settings/plugins/core"
      silent
      @validate="onFormValidate"
    />
    <XForm
      v-model="mutualTLS"
      :schema="mutualTLSSchema"
      api-upload="settings/plugins/gui"
      silent
      @validate="onFormValidate"
    />
    <div>&nbsp;</div>
    <XButton
      id="SaveSettings"
      title="Run"
      type="primary"
      :disabled="!canUpdateSettings"
      @click="saveCertificateSettings"
    >Save</XButton>
    <div
      v-if="error"
      class="header header-error"
    >{{ message }}</div>
    <XToast
      v-if="toasterMessage"
      v-model="toasterMessage"
      :timeout="toastTimeout"
    />
  </div>
</template>
<script>

import { mapActions, mapState, mapGetters } from 'vuex';
import _get from 'lodash/get';
import XToast from '@axons/popover/Toast.vue';
import {
  LOAD_PLUGIN_CONFIG,
  GET_CERTIFICATE_DETAILS, SET_CERTIFICATE_SETTINGS, DELETE_CSR,
  RESET_CERTIFICATE_SETTINGS, DOWNLOAD_CSR,
} from '@store/modules/settings';
import { DATE_FORMAT } from '@store/getters';
import { formatDate } from '@constants/utils';
import {
  generateCSRAction, importCertAndKeyAction, importCSRAction, resetSystemDefaultsAction,
} from '@constants/settings';
import XModal from '@axons/popover/Modal/index.vue';
import XForm from '@neurons/schema/Form.vue';
import XInstallCSRModal from '../certificate/InstallCSRModal.vue';
import XImportCertAndKeyModal from '../certificate/ImportCertAndKeyModal.vue';
import XCreateCSRModal from '../certificate/CreateCSRModal.vue';
import XCertificateActions from '../certificate/CertificateActions.vue';


export default {
  name: 'XCertificateSettings',
  components: {
    XToast,
    XModal,
    XForm,
    XCertificateActions,
    XImportCertAndKeyModal,
    XInstallCSRModal,
    XCreateCSRModal,
  },
  data() {
    return {
      certDetails: {
        issued_to: '',
        alternative_Names: '',
        issued_by: '',
        sha1_fingerprint: '',
        expires_on: '',
      },
      error: false,
      message: '',
      toasterMessage: '',
      toastTimeout: 5000,
      formValid: false,
      importCertAndKeyActive: false,
      importCsrActive: false,
      generateCsrActive: false,
      resetSystemDefaultsActive: false,
      SSLTrust: {
        ssl_trust_settings: {
          enabled: false,
          ca_files: [],
        },
      },
      mutualTLS: {
        mutual_tls_settings: {
          enabled: false,
          mandatory: false,
          ca_certificate: '',
        },
      },
      downloading: false,
    };
  },
  computed: {
    ...mapState({
      coreService(state) {
        return _get(state, 'settings.configurable.core.CoreService', {});
      },
      guiService(state) {
        return _get(state, 'settings.configurable.gui.GuiService', {});
      },
    }),
    isActiveCSR() {
      return _get(this.coreService, 'config.csr_settings.status');
    },
    sslTrustSettings() {
      return _get(this.coreService, 'config.ssl_trust_settings');
    },
    csrPendingName() {
      return _get(this.coreService, 'config.csr_settings.subject_name');
    },
    csrPendingSince() {
      return formatDate(
        _get(this.coreService, 'config.csr_settings.submission_date', ''), 'date', this.dateFormat,
      ).split(' ')[0];
    },
    sslTrustItems() {
      const items = _get(this.coreService, 'schema.items', []).find((item) => item.name === 'ssl_trust_settings');
      if (items) {
        delete items.hidden;
        return [items];
      }
      return [];
    },
    sslTrustRequiredItems() {
      const items = _get(this.coreService, 'schema.items', []).find((item) => item.name === 'ssl_trust_settings');
      return items ? items.required : [];
    },
    mutualTLSSettings() {
      return _get(this.guiService, 'config.mutual_tls_settings');
    },
    mutualTLSItems() {
      const items = _get(this.guiService, 'schema.items', []).find((item) => item.name === 'mutual_tls_settings');
      if (items) {
        delete items.hidden;
        return [items];
      }
      return [];
    },
    mutualTLSRequiredItems() {
      const items = _get(this.guiService, 'schema.items', []).find((item) => item.name === 'mutual_tls_settings');
      return items ? items.required : [];
    },
    canUpdateSettings() {
      return this.$can(this.$permissionConsts.categories.Settings,
        this.$permissionConsts.actions.Update);
    },
    ...mapGetters({
      dateFormat: DATE_FORMAT,
    }),
    sslTrustSchema() {
      return {
        type: 'array',
        required: this.sslTrustRequiredItems,
        items: this.sslTrustItems,
      };
    },
    mutualTLSSchema() {
      return {
        type: 'array',
        required: this.mutualTLSRequiredItems,
        items: this.mutualTLSItems,
      };
    },
    issuedTo() {
      return this.certDetails.issued_to;
    },
    alternativeNames() {
      return this.certDetails.alternative_names;
    },
    issuedBy() {
      return this.certDetails.issued_by;
    },
    sha1Fingerprint() {
      return this.certDetails.sha1_fingerprint;
    },
    expiresOn() {
      return this.certDetails.expires_on;
    },
  },
  watch: {
    sslTrustSettings: {
      handler: 'setSSLTrustSettings',
      immediate: true,
    },
    mutualTLSSettings: {
      handler: 'setMutualTLSSettings',
      immediate: true,
    },
  },
  mounted() {
    this.updateCertificateDetailsView();
  },
  methods: {
    ...mapActions({
      getCertificateDetails: GET_CERTIFICATE_DETAILS,
      setCertificateSettings: SET_CERTIFICATE_SETTINGS,
      deleteCSR: DELETE_CSR,
      resetCertificateSettings: RESET_CERTIFICATE_SETTINGS,
      loadPluginConfig: LOAD_PLUGIN_CONFIG,
      downloadCsr: DOWNLOAD_CSR,
    }),
    setSSLTrustSettings() {
      this.SSLTrust.ssl_trust_settings = this.sslTrustSettings;
    },
    setMutualTLSSettings() {
      this.mutualTLS.mutual_tls_settings = this.mutualTLSSettings;
    },
    saveCertificateSettings() {
      this.setCertificateSettings({
        ssl_trust: this.SSLTrust.ssl_trust_settings,
        mutual_tls: this.mutualTLS.mutual_tls_settings,
      }).then(() => {
        this.toasterMessage = 'Certificate settings saved successfully';
        this.refreshSettings();
      }).catch((error) => {
        this.toasterMessage = error.response.data.message;
      });
    },
    setTostaterMsg(msg) {
      this.toasterMessage = msg;
    },
    onFormValidate(valid) {
      this.formValid = valid;
    },
    cancelCSR() {
      this.deleteCSR().then(() => {
        this.toasterMessage = 'CSR deleted successfully';
        this.refreshSettings();
      }).catch((error) => {
        this.toasterMessage = error.response.data.message;
      });
    },
    updateCertificateDetailsView() {
      this.getCertificateDetails().then((response) => {
        if (!response.data) {
          this.certDetails.certIssuedTo = this.certDetails.certAlternativeNames = this.certDetails.certIssuedBy = this.certDetails.certSha1Fingerprint = this.certDetails.certExpiresOn = '';
        }
        this.certDetails = response.data;
        this.certDetails.alternative_names = this.certDetails.alternative_names.join(', ');
      });
    },
    async refreshSettings() {
      await this.loadPluginConfig({
        pluginId: 'gui',
        configName: 'GuiService',
      });
      await this.loadPluginConfig({
        pluginId: 'core',
        configName: 'CoreService',
      });
      this.updateCertificateDetailsView();
    },
    resetToDefaults() {
      this.resetCertificateSettings().then(() => {
        this.toasterMessage = 'Certificate settings reset successfully';
        this.refreshSettings();
        this.actionToggle(resetSystemDefaultsAction);
      }).catch((error) => {
        this.toasterMessage = error.response.data.message;
      });
    },
    actionToggle(action) {
      switch (action) {
        case generateCSRAction:
          this.generateCsrActive = !this.generateCsrActive;
          break;
        case importCertAndKeyAction:
          this.importCertAndKeyActive = !this.importCertAndKeyActive;
          break;
        case importCSRAction:
          this.importCsrActive = !this.importCsrActive;
          break;
        case resetSystemDefaultsAction:
          this.resetSystemDefaultsActive = !this.resetSystemDefaultsActive;
          break;
      }
    },
    startDownload() {
      this.downloading = true;
      this.downloadCsr().then(() => {
        this.downloading = false;
      }).catch((error) => {
        this.downloading = false;
        this.showToaster(error.response.data.message, this.toastTimeout);
      });
    },
  },
};
</script>

<style lang="scss">
  .x-certificate-settings {
    .header {
      font-size: 18px;
      font-weight: 300 !important;
      color: black;
      font-weight: normal;
    }
    .header-title {
      font-size: 14px;
      color: rgba(0,0,0,.87);
      display: inline-block;
      width: 10%;
    }
    .header-text {
      font-size: 14px;
      display: inline-block;
      margin-bottom: 5px;
      font-weight: 200 !important;
      width: 89%;
    }
    .header-error {
      margin: 5px 0;
      color: $indicator-error;
      font-weight: 300 !important;
    }
    .x-form > .x-array-edit > div > div > .list {
      grid-template-columns: 1fr !important;
      grid-gap: 0 !important;
    }
    .x-modal .x-button {
      width: auto;
    }
  }
</style>
