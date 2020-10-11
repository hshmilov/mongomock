<template>
  <XFeedbackModal
    v-model="isActive"
    :handle-save="saveFields"
    :message="`Custom data saved`"
    approve-text="Save"
    :disabled="!valid"
    @change="handleChange"
  >
    <XCustomFields
      v-model="customAdapterData"
      :module="module"
      :fields="customFields"
      @validate="validateFieldsEditor"
    />
  </XFeedbackModal>
</template>

<script>
import { mapActions } from 'vuex';
import actionModal from '@mixins/action_modal';
import entityCustomData from '@mixins/entity_custom_data';
import { FETCH_DATA_FIELDS } from '@store/actions';
import XFeedbackModal from './FeedbackModal.vue';
import XCustomFields from '@networks/entities/view/CustomFields.vue';

export default {
  name: 'XAddCustomDataModal',
  components: { XFeedbackModal, XCustomFields },
  mixins: [entityCustomData, actionModal],
  data() {
    return {
      customAdapterData: [],
      valid: true,
    };
  },
  methods: {
    ...mapActions(
      {
        fetchDataFields: FETCH_DATA_FIELDS,
      },
    ),
    saveFields() {
      return this.saveEntityCustomData(this.entities, this.customAdapterData).then(() => {
        this.fetchDataFields({ module: this.module });
        this.initCustomFields();
        this.$emit('done');
      });
    },
    initCustomFields() {
      this.customAdapterData = [];
    },
    handleChange(active) {
      if (!active) {
        this.initCustomFields();
      }
    },
    validateFieldsEditor(valid) {
      this.valid = valid;
    },
  },
};
</script>

<style lang="scss">

</style>
