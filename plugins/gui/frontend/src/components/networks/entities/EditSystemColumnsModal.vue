<template>
  <XEditColumnsModal
    :title="title"
    approve-text="Save"
    :current-fields="currentFields"
    :module="module"
    @approve="onApprove"
    @close="$emit('close')"
    @update-unsaved-fields="updateUnsavedFields"
  />
</template>

<script>
import { Modal } from 'ant-design-vue';
import XEditColumnsModal from '@networks/entities/EditColumnsModal.vue';
import { mapActions, mapState, mapGetters } from 'vuex';
import _get from 'lodash/get';
import _snakeCase from 'lodash/snakeCase';
import { GET_SYSTEM_COLUMNS } from '../../../store/getters';
import { SAVE_SYSTEM_DEFAULT_COLUMNS } from '../../../store/actions';

export default {
  name: 'XEditSystemColumnsModal',
  components: {
    XEditColumnsModal,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
  },
  computed: {
    ...mapState({
      querySearchTemplate(state) {
        return _get(state, `${this.module}.view.query.meta.searchTemplate`, null);
      },
    }),
    ...mapGetters({
      getSystemColumns: GET_SYSTEM_COLUMNS,
    }),
    title() {
      if (this.querySearchTemplate) {
        return `Edit System Search Default (${this.querySearchTemplate.name})`;
      }
      return 'Edit System Default';
    },
    columnsGroupName() {
      return !this.querySearchTemplate ? 'default' : _snakeCase(this.querySearchTemplate.name);
    },
    currentFields() {
      return this.getSystemColumns(this.module, this.columnsGroupName);
    },
  },
  created() {
    this.unsavedFields = this.currentFields;
  },
  methods: {
    ...mapActions({
      saveSystemDefaultColumns: SAVE_SYSTEM_DEFAULT_COLUMNS,
    }),
    updateUnsavedFields(unsavedFields) {
      this.unsavedFields = unsavedFields;
    },
    onApprove() {
      const title = this.querySearchTemplate
        ? `This will modify the system search default (${this.querySearchTemplate.name}) view for all users in the system.`
        : 'This will modify the system default view for all users in the system.';

      Modal.confirm({
        title,
        content: 'Do you wish to continue?',
        okText: 'Save',
        cancelText: 'Cancel',
        centered: true,
        onOk: () => {
          this.saveSystemDefaultColumns({
            module: this.module,
            columnsGroupName: this.columnsGroupName,
            fields: this.unsavedFields,
          });
          this.closeModal();
        },
      });
    },
    closeModal() {
      this.$emit('close');
    },
  },
};
</script>
