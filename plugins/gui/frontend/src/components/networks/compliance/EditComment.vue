<template>
  <div class="x-edit-comment">
    <div class="edit_comment">
      <ATextarea
        ref="textarea"
        v-model="text"
        placeholder="Add Comment"
        :auto-size="{ minRows: 1, maxRows: 2 }"
        maxlength="150"
        class="edit_comment__text"
        :disabled="disabled"
        @keydown.native="$emit('remove-error')"
      />
      <span class="edit_comment__select_account">
        <ASelect
          v-model="account"
          placeholder="Select Account"
          class="edit_comment__account"
          :get-popup-container="getSelectContainer"
          :disabled="disabled"
          @change="$emit('remove-error')"
        >
          <ASelectOption value="All">
            All
          </ASelectOption>
          <ASelectOption
            v-for="item in accounts"
            :key="item"
            :value="item"
          >
            {{ item }}
          </ASelectOption>
        </ASelect>
      </span>
      <span>
        <span
          v-if="!add"
          class="edit_comment__actions"
        >
          <XButton
            type="link"
            icon="close"
            title="Cancel"
            @click="cancel"
          />
          <XButton
            type="link"
            icon="check"
            title="Save"
            @click="saveItem"
          />
        </span>
      </span>
    </div>
    <XButton
      v-if="add"
      type="link"
      icon="plus-circle"
      :disabled="isDataEmpty || disabled"
      class="add_comment"
      @click="saveItem"
    >
      Add Comment
    </XButton>
  </div>
</template>

<script>
import _get from 'lodash/get';
import {
  Select, Input,
} from 'ant-design-vue';
import XButton from '@axons/inputs/Button.vue';

export default {
  name: 'XEditComment',
  components: {
    XButton,
    ASelect: Select,
    ASelectOption: Select.Option,
    ATextarea: Input.TextArea,
  },
  props: {
    data: {
      type: Object,
      default: () => ({ text: '' }),
    },
    accounts: {
      type: Array,
      default: () => [],
    },
    add: {
      type: Boolean,
      default: false,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      text: '',
      account: undefined,
    };
  },
  computed: {
    isDataEmpty() {
      return !this.text.trim() || !this.account;
    },
    hasDataChanged() {
      return this.text !== this.data.text || this.account !== this.data.account;
    },
  },
  created() {
    this.text = _get(this, 'data.text', '');
    this.account = _get(this, 'data.account');
    if (!this.add) {
      this.focusTextarea();
    }
  },
  methods: {
    getSelectContainer() {
      return this.$el.querySelector('.x-edit-comment .edit_comment__select_account');
    },
    saveItem() {
      if (this.hasDataChanged) {
        const { text, account } = this;
        this.$emit('save', { text, account, index: this.data.index });
      } else {
        this.$emit('cancel');
      }
      this.text = '';
      this.account = undefined;
    },
    focusTextarea() {
      this.$nextTick(() => {
        this.$refs.textarea.$el.focus();
      });
    },
    cancel() {
      this.$emit('cancel');
    },
  },
};
</script>

<style lang="scss">
  .x-edit-comment {
    .edit_comment {
      display: flex;
      &__text {
        width: 461px;
        margin-right: 5px;
        resize: none;
      }
      &__account {
        width: 195px;
      }
      &__actions {
        display: flex;
      }
      &__select_account {
        display: table;
      }
    }
    .add_comment {
      padding: 0;
      margin-bottom: 15px;
    }
  }
</style>
