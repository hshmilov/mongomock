<template>
  <AModal
    class="x-compliance-active-rules"
    id="cis_active_rules"
    :visible="visible"
    :closable="false"
    width="700px"
    height="550px"
    :centered="true"
    :title="title"
    @cancel="handleDismiss"
  >
    <div class="rules-selection">
      <XCombobox
        v-model="activeRules"
        height="30"
        :selection-display-limit="0"
        :items="allCisRules"
        label="Rule"
        multiple
        keep-open
        :allow-create-new="false"
        :hide-quick-selections="true"
        :menu-props="{maxWidth: 265}"
        :custom-sort="customSort"
      />
    </div>

    <template slot="footer">
      <XButton
        type="link"
        @click="handleDismiss"
      >
        Cancel
      </XButton>
      <XButton
        type="primary"
        @click="handleApprove"
      >
        Save
      </XButton>
    </template>
  </AModal>
</template>

<script>
import { Modal } from 'ant-design-vue';
import XButton from '@axons/inputs/Button.vue';
import XCombobox from '@axons/inputs/combobox/index.vue';

export default {
  name: 'XComplianceActiveRules',
  components: {
    AModal: Modal,
    XButton,
    XCombobox,
  },
  props: {
    value: {
      type: Array,
      default: () => [],
    },
    visible: {
      type: Boolean,
      default: false,
    },
    allCisRules: {
      type: Array,
      default: () => [],
    },
    customSort: {
      type: Function,
      default: null,
    },
    cisTitle: {
      type: String,
      default: '',
    },
  },
  computed: {
    activeRules: {
      get() {
        return this.value;
      },
      set(value) {
        this.$emit('input', value);
      },
    },
    title() {
      return `${this.cisTitle} Score Enabled Rules`;
    },
  },
  methods: {
    handleDismiss() {
      this.$emit('close');
    },
    handleApprove() {
      this.$emit('save-rules');
      this.handleDismiss();
    },
  },
};
</script>

<style scoped>

</style>
