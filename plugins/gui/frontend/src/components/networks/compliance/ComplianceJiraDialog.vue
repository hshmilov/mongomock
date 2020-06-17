<template>
  <XFeedbackModal
    v-model="isActive"
    class="x-compliance-jira-dialog"
    :handle-save="createJira"
    :message="message"
    :approve-text="title"
    :disabled="!formValid"
    @change="$emit('close')"
  >
    <div class="header">
      <div class="header__title">
        <XTitle
          logo="actions/create_jira_incident"
          :height="48"
        >{{ title }} </XTitle>
      </div>
      <div class="header__subtitle">
        CSV with results will be attached to the Jira Issue.
      </div>
    </div>

    <div class="body">
      <div class="body__title">
        Configuration
      </div>
      <XForm
        v-if="actionSchema"
        v-model="jiraProperties"
        :schema="actionSchema"
        @validate="validateForm"
      />
    </div>
  </XFeedbackModal>
</template>

<script>
import { mapState } from 'vuex';
import { createJiraIssue } from '@api/compliance';
import { jiraFormFields } from '@constants/compliance';
import XFeedbackModal from '@neurons/popover/FeedbackModal.vue';
import XTitle from '@axons/layout/Title.vue';
import XForm from '@neurons/schema/Form.vue';
import actionsMixin from '../../../mixins/actions';

export default {
  name: 'XComplianceJiraDialog',
  components: {
    XFeedbackModal, XTitle, XForm,
  },
  mixins: [actionsMixin],
  props: {
    message: {
      type: String,
      default: 'Jira issue created successfully',
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
    rules: {
      type: Array,
      default: () => [],
    },
    categories: {
      type: Array,
      default: () => [],
    },
    failedOnly: {
      type: Boolean,
      default: false,
    },
    isActive: {
      type: Boolean,
      default: false,
    },
    aggregatedView: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      title: 'Create Jira Issue',
      jiraProperties: {
        project_key: null,
        issue_type: null,
        incident_title: null,
        incident_description: null,
        assignee: null,
        labels: null,
        components: null,
      },
      validity: {
        fields: [], error: '',
      },
      formValid: false,
      actionName: 'create_jira_incident',
    };
  },
  computed: {
    ...mapState({
      schemaFields(state) {
        return state[this.module].view.schema_fields;
      },
    }),
    actionConfig() {
      if (!this.actionsDef || !this.actionName) return {};

      return this.actionsDef[this.actionName];
    },
    actionSchema() {
      if (!this.actionConfig) return {};
      const items = this.actionConfig.schema.items.filter((item) => jiraFormFields.items.includes(item.name));
      const required = this.actionConfig.schema.required.filter((item) => jiraFormFields.required.includes(item));
      return { ...this.actionConfig.schema, items, required };
    },
  },
  methods: {
    validateForm(valid) {
      this.formValid = valid;
    },
    async createJira() {
      if (!this.formValid) return;
      try {
        await createJiraIssue(
          this.cisName,
          this.accounts,
          this.jiraProperties,
          this.schemaFields,
          this.cisTitle,
          this.rules,
          this.categories,
          this.failedOnly,
          this.aggregatedView,
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
  .x-compliance-jira-dialog {
    .modal-body .header {
      font-size: 20px;
      padding: 12px;
      display: block;
      &__title {
        display: flex;
      }
      &__subtitle {
        padding-top: 5px;
        font-size: 14px;
      }
    }
    .body {
      padding: 12px;
      &__title {
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
    .modal-footer .ant-btn-primary {
      width: 135px;
    }
  }
</style>
