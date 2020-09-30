<template>
  <div class="x-compliance-components">
    <span class="error-input indicator-error--text">{{ error }}</span>
    <EditComment
      v-if="canEditComplianceComments"
      :accounts="accountsSorted"
      :add="true"
      :disabled="isInEditingMode"
      @save="saveItem"
      @cancel="cancelEdit"
      @remove-error="removeError"
    />
    <div
      v-for="(item, index) in comments"
      :key="index"
      class="comments"
    >
      <EditComment
        v-if="index === editIndex"
        :data="{...item, index}"
        :accounts="accountsSorted"
        @save="saveItem"
        @cancel="cancelEdit"
      />
      <div
        v-else
        class="comment"
      >
        <span class="comment__text">{{ item.text }}</span>
        <span class="comment__account">{{ item.account }}</span>
        <span
          v-if="canEditComplianceComments"
          class="comment__actions"
        >
          <XButton
            type="link"
            class="ant-btn-icon-only edit"
            :disabled="isInEditingMode"
            title="Edit"
            @click="editItem(index)"
          >
            <XIcon
              family="action"
              type="edit"
            />
          </XButton>
          <XButton
            type="link"
            class="ant-btn-icon-only delete"
            title="Delete"
            :disabled="isInEditingMode"
            @click="deleteItem(index)"
          >
            <XIcon
              family="action"
              type="remove"
            />
          </XButton>
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import _sortBy from 'lodash/sortBy';
import { updateComplianceComments } from '@api/compliance';
import EditComment from './EditComment.vue';

export default {
  name: 'XComplianceComments',
  components: {
    EditComment,
  },
  props: {
    comments: {
      type: Array,
      default: () => [],
    },
    accounts: {
      type: Array,
      default: () => [],
    },
    cisName: {
      type: String,
      default: '',
    },
    section: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      editIndex: null,
      error: '',
    };
  },
  computed: {
    accountsSorted() {
      return _sortBy(this.accounts);
    },
    isInEditingMode() {
      return this.editIndex !== null;
    },
    canEditComplianceComments() {
      return this.$can(this.$permissionConsts.categories.Compliance,
        this.$permissionConsts.actions.Update,
        this.$permissionConsts.categories.Comments);
    },
  },
  methods: {
    handleChange(value, key, column) {
      const newData = [...this.data];
      const target = newData.filter((item) => key === item.key)[0];
      if (target) {
        target[column] = value;
        this.data = newData;
      }
    },
    editItem(key) {
      this.removeError();
      this.editIndex = key;
    },
    deleteItem(index) {
      this.removeError();
      this.$safeguard.show({
        text: `You are about to delete a comment.<br/>
              This comment will no longer be visible for all users.<br/>
              Are you sure you want to delete this comment?`,
        confirmText: 'Delete',
        onConfirm: async () => {
          const comments = this.comments.filter((comment, i) => i !== index);
          const result = await updateComplianceComments({
            name: this.cisName, section: this.section, index,
          });
          this.updateResult(result, comments);
        },
      });
    },
    async saveItem(data) {
      const { index, ...newComment } = data;
      let comments = [];
      if (index !== undefined) {
        comments = this.comments.map(
          (item, i) => (index === i ? { text: newComment.text, account: newComment.account } : item),
        );
      } else {
        comments = [newComment, ...this.comments];
      }
      const result = await updateComplianceComments({
        name: this.cisName, section: this.section, comment: newComment, index,
      });
      this.updateResult(result, comments);
      this.cancelEdit();
    },
    cancelEdit() {
      this.editIndex = null;
    },
    removeError() {
      this.error = '';
    },
    updateResult(result, comments) {
      if (result.success) {
        this.$emit('updateComments', { section: this.section, comments });
      } else {
        this.error = result.error;
      }
    },
  },
};
</script>

<style lang="scss">
  .x-compliance-components {
    .comment {
      display: flex;
      margin-bottom: 20px;
      &__actions{
        display: flex;
        .x-button {
          width: 38px;
        }
        svg {
          width: 20px;
          height: 20px;
        }
        .anticon-close svg,
        .anticon-check svg {
          width: 16px;
          height: 16px;
        }
      }
      &__text {
        width: 461px;
        margin-right: 5px;
      }
      &__account {
        width: 195px;
      }
    }
  }
</style>
