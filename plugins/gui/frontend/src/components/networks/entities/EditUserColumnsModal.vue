<template>
  <XEditColumnsModal
    title="Edit Columns"
    approve-text="Done"
    :current-fields="currentFields"
    :module="module"
    @approve="onApprove"
    @close="closeModal"
    @update-unsaved-fields="updateUnsavedFields"
    @reset-user-fields="$emit('reset-user-fields')"
  >
    <XButton
      slot="extraActions"
      type="link"
      class="save-default-button"
      :disabled="isCurrentFieldsEmpty"
      @click="saveUserDefault"
    >{{ saveButtonText }}</XButton>
  </XEditColumnsModal>
</template>

<script>
import XEditColumnsModal from '@networks/entities/EditColumnsModal.vue';
import { saveUserTableColumnGroup } from '@api/user-preferences';
import { mapState, mapMutations } from 'vuex';
import _get from 'lodash/get';
import _snakeCase from 'lodash/snakeCase';
import _isEmpty from 'lodash/isEmpty';
import { SHOW_TOASTER_MESSAGE, UPDATE_DATA_VIEW } from '@store/mutations';

export default {
  name: 'XEditUserColumnsModal',
  components: {
    XEditColumnsModal,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    userFieldsGroups: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      unsavedFields: [],
    };
  },
  computed: {
    ...mapState({
      currentFields(state) {
        return _get(state, `${this.module}.view.fields`, []);
      },
      querySearchTemplate(state) {
        return _get(state, `${this.module}.view.query.meta.searchTemplate`, null);
      },
    }),
    isCurrentFieldsEmpty() {
      return _isEmpty(this.currentFields);
    },
    saveButtonText() {
      return !this.querySearchTemplate
        ? 'Save as User Default'
        : `Save as User Search Default (${this.querySearchTemplate.name})`;
    },
    columnsGroupName() {
      return !this.querySearchTemplate ? 'default' : _snakeCase(this.querySearchTemplate.name);
    },
  },
  created() {
    this.unsavedFields = this.currentFields;
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    updateUnsavedFields(unsavedFields) {
      this.unsavedFields = unsavedFields;
    },
    onApprove() {
      this.updateView({
        module: this.module,
        view: {
          fields: this.unsavedFields,
        },
      });
      this.$emit('done');
      this.closeModal();
    },
    async saveUserDefault() {
      let message = 'Successfully saved user default view';
      if (this.querySearchTemplate) {
        message = `Successfully saved user search default view (${this.querySearchTemplate.name})`;
      }
      try {
        await saveUserTableColumnGroup(this.module, this.unsavedFields, this.columnsGroupName);
        const updatedFieldsGroups = {
          ...this.userFieldsGroups,
          [this.columnsGroupName]: this.unsavedFields,
        };
        this.$emit('update:user-fields-groups', updatedFieldsGroups);
        this.onApprove();
      } catch (error) {
        message = 'Error saving as default view';
      }
      this.showToasterMessage({ message });
    },
    closeModal() {
      this.$emit('close');
    },
  },
};
</script>

<style lang="scss">
  .save-default-button.x-button {
    padding-left: 0;
  }
</style>
