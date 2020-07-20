<template>
  <XFeedbackModal
    v-model="isActive"
    :handle-save="unlinkEntities"
    :message="`${module} were unlinked`"
    approve-text="Save"
  >
    <div class="warn-delete">
      You are about to unlink {{ selectionCount }} {{ module }}.
      This means that each of the adapter {{ module }}
      inside will become a standalone axonius entity.
    </div>
  </XFeedbackModal>
</template>

<script>
import { mapActions } from 'vuex';
import actionModal from '@mixins/action_modal';
import { UNLINK_DATA } from '@store/actions';
import XFeedbackModal from './FeedbackModal.vue';

export default {
  name: 'XUnlinkModal',
  components: { XFeedbackModal },
  mixins: [actionModal],
  methods: {
    ...mapActions(
      {
        unlinkData: UNLINK_DATA,
      },
    ),
    unlinkEntities() {
      return this.unlinkData({
        module: this.module, data: this.entities,
      }).then(() => this.$emit('done'));
    },
  },
};
</script>

<style lang="scss">

</style>
