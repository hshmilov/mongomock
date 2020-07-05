<template>
  <XModal
    approve-text="Create"
    :disabled="!formValid"
    @confirm="createCertificateRequest"
    @close="cancelCreateCSR"
  >
    <div slot="body">
      <div>
        <div class="content">
          <h2>Create Certificate Signing Request</h2>
          <XForm
            v-model="CSRCreate"
            :schema="createCSRSchema"
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
import { CREATE_CSR } from '../../../store/modules/settings';

export default {
  name: 'XCreateCSRModal',
  components: { XModal, XForm },
  data() {
    return {
      formValid: false,
      CSRCreate: {
        hostname: '',
        alt_names: '',
        organization: '',
        OU: '',
        location: '',
        state: '',
        country: '',
        email: '',
      },
      CSRCreateItems: [
        {
          name: 'hostname',
          title: 'Domain name',
          type: 'string',
        },
        {
          name: 'alt_names',
          title: 'Alternative Names',
          type: 'string',
        },
        {
          name: 'organization',
          title: 'Organization',
          type: 'string',
        },
        {
          name: 'OU',
          title: 'Organization Unit',
          type: 'string',
        },
        {
          name: 'location',
          title: 'City/Location',
          type: 'string',
        },
        {
          name: 'state',
          title: 'State/Province',
          type: 'string',
        },
        {
          name: 'country',
          title: 'Country',
          type: 'string',
          description: 'Only 2 letters',
        },
        {
          name: 'email',
          title: 'Email',
          type: 'string',
          format: 'email',
        },
      ],
      requiredItems: ['hostname'],
    };
  },
  computed: {
    createCSRSchema() {
      return {
        type: 'array',
        required: this.requiredItems,
        items: this.CSRCreateItems,
      };
    },
  },
  methods: {
    ...mapActions({
      createCSR: CREATE_CSR,
    }),
    createCertificateRequest() {
      this.createCSR(this.CSRCreate).then(() => {
        this.$emit('toaster', 'CSR created successfully');
        this.$emit('refresh');
        window.location.href = '/api/certificate/csr';
      }).catch((error) => {
        this.$emit('toaster', error.response.data.message);
      }).then(() => {
        this.$emit('closed');
      });
    },
    cancelCreateCSR() {
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
