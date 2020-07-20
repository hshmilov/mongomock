<template>
  <XFeedbackModal
    v-model="isActive"
    :handle-save="linkEntities"
    :message="`${module} were linked`"
    :disabled="selectionCount > 10"
    approve-text="Save"
  >
    <div
      v-if="selectionCount > 10"
      class="table-error"
    >Maximal amount of {{ module }} to link is 10</div>
    <div
      v-else
      class="warn-delete"
    >You are about to link {{ selectionCount }} {{ module }}.</div>
  </XFeedbackModal>
</template>

<script>
import { mapActions } from 'vuex';
import actionModal from '@mixins/action_modal';
import { LINK_DATA } from '@store/actions';
import XFeedbackModal from './FeedbackModal.vue';

export default {
  name: 'XLinkModal',
  components: { XFeedbackModal },
  mixins: [actionModal],
  methods: {
    ...mapActions(
      {
        linkData: LINK_DATA,
      },
    ),
    linkEntities() {
      return this.linkData({
        module: this.module, data: this.entities,
      }).then(() => this.$emit('done'));
    },
  },
};
</script>

<style lang="scss">

</style>
