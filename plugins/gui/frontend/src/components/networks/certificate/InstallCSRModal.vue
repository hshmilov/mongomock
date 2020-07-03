<template>
  <XModal
    approve-text="Import"
    :disabled="!formValid"
    @confirm="importCertificate"
    @close="cancelInstallCSR"
  >
    <div slot="body">
      <div>
        <div class="content">
          <h2>Install Signed Certificate</h2>
          <XForm
            v-model="CSRInstall"
            :schema="installCSRSchema"
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
import { mapActions } from 'vuex';
import XForm from '../../neurons/schema/Form.vue';
import XModal from '../../axons/popover/Modal/index.vue';
import { IMPORT_SIGNED_CERTIFICATE } from '../../../store/modules/settings';

export default {
  name: 'XInstallCSRModal',
  components: { XModal, XForm },
  data() {
    return {
      formValid: false,
      CSRInstall: {
        cert_file: null,
      },
      CSRIntallItems: [
        {
          name: 'cert_file',
          title: 'Certificate file',
          description: 'The binary contents of the singed CSR',
          type: 'file',
        },
      ],
      requiredItems: ['cert_file'],
    };
  },
  computed: {
    installCSRSchema() {
      return {
        type: 'array',
        required: this.requiredItems,
        items: this.CSRIntallItems,
      };
    },
  },
  methods: {
    ...mapActions({
      importSignedCertificate: IMPORT_SIGNED_CERTIFICATE,
    }),
    importCertificate() {
      this.importSignedCertificate(this.CSRInstall.cert_file).then(() => {
        this.$emit('toaster', 'Certificate was added successfully');
        this.$emit('refresh');
      }).catch((error) => {
        this.$emit('toaster', error.response.data.message);
      }).then(() => {
        this.$emit('closed');
      });
    },
    cancelInstallCSR() {
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
