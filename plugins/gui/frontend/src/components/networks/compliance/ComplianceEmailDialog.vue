<template>
  <XFeedbackModal
    class="compliance_email_dialog"
    v-model="isActive"
    :handle-save="sendEmail"
    :message="message"
    :approve-text="title"
    :disabled="!formValid"
  >
    <div class="email-header">
      <div class="email-title">
        <XTitle
          logo="actions/send_emails"
          :height="48"
        >{{ title }} </XTitle>
      </div>
      <div class="email-subtitle">
        CSV with results will be attached to the Email.
      </div>
    </div>

    <div class="body">
      <div class="body-title">
        Configuration
      </div>
      <XForm
        ref="mail_form"
        v-model="mail_properties"
        :schema="mailSchema"
        @validate="validateForm"
      />
    </div>
  </XFeedbackModal>
</template>

<script>
import { mapState } from 'vuex';
import { sendComplianceEmail } from '@api/compliance';
import { emailFormFields } from '@constants/compliance';
import XFeedbackModal from '@neurons/popover/FeedbackModal.vue';
import XTitle from '@axons/layout/Title.vue';
import XForm from '@neurons/schema/Form.vue';

export default {
  name: 'XComplianceEmailDialog',
  components: {
    XFeedbackModal, XTitle, XForm,
  },
  props: {
    message: {
      type: String,
      default: 'Email sent successfully',
    },
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
      isActive: false,
      title: 'Send Email',
      mail_properties: {
        mailSubject: null,
        mailMessage: '',
        emailList: [],
        emailListCC: [],
        accountAdmins: false,
      },
      validity: {
        fields: [], error: '',
      },
      formValid: false,
    };
  },
  computed: {
    ...mapState({
      schema_fields(state) {
        return state[this.module].view.schema_fields;
      },
    }),
    mailSchema() {
      return {
        name: 'mail_config',
        title: '',
        items: emailFormFields[this.cisName],
        required: [
          'accountAdmins', 'mailSubject', 'emailList',
        ],
        type: 'array',
      };
    },
  },
  methods: {
    validateForm(valid) {
      this.formValid = valid;
    },
    activate() {
      this.isActive = true;
    },
    async sendEmail() {
      if (!this.formValid) return;
      try {
        await sendComplianceEmail(
          this.cisName,
          this.accounts,
          this.mail_properties,
          this.schema_fields,
          this.cisTitle,
        );
        return;
      } catch (error) {
        this.formValid = false;
        throw error;
      }
    },
  },
};
</script>


<style lang="scss">
  .compliance_email_dialog {
    .email-header {
      font-size: 20px;
      padding: 12px;
      display: block;
      .email-title {
        display: flex;
      }
      .email-subtitle {
        padding-top: 5px;
        font-size: 14px;
      }
    }
    .body {
      padding: 12px;
      .body-title {
        font-size: 16px;
        font-weight: 400;
        margin-bottom: 10px;
      }

      .x-form > .x-array-edit {
        grid-template-columns: 1fr;
        grid-gap: 24px 0;
        display: grid;
      }
    }
  }
</style>
