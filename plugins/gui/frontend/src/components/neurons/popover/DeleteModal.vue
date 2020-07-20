<template>
  <XFeedbackModal
    v-model="isActive"
    :handle-save="deleteEntities"
    :message="`Deleted ${module}`"
    approve-text="Delete"
  >
    <div class="warn-delete">
      You are about to delete {{ selectionCount }} {{ module }}.
    </div>
    <div>These {{ module }} could reappear in further scans
      if they are not removed or detached.</div>
    <div>Are you sure you want to delete these {{ module }}?</div>
  </XFeedbackModal>
</template>

<script>
import { mapActions } from 'vuex';
import actionModal from '@mixins/action_modal';
import { DELETE_DATA } from '@store/actions';
import XFeedbackModal from './FeedbackModal.vue';

export default {
  name: 'XDeleteModal',
  components: { XFeedbackModal },
  mixins: [actionModal],
  methods: {
    ...mapActions(
      {
        deleteData: DELETE_DATA,
      },
    ),
    deleteEntities() {
      return this.deleteData({
        module: this.module, selection: this.entities,
      }).then(() => this.$emit('done'));
    },
  },
};
</script>

<style lang="scss">

</style>
