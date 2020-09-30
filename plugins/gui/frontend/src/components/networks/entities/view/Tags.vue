<template>
  <div class="x-entity-tags">
    <div class="tag-edit">
      <XButton
        type="link"
        :disabled="userCannotEditDevices"
        @click="activateTag"
      >Edit Tags</XButton>
    </div>
    <div class="tag-list w-lg">
      <template v-for="(tag, i) in tags">
        <div :key="i">
          <VChip class="tag">
            {{ tag }}
          </VChip>
        </div>
        <XButton
          :key="tag"
          type="link"
          :disabled="userCannotEditDevices"
          @click="removeTag(tag)"
        >Remove</XButton>
      </template>
    </div>
    <XTagModal
      ref="tagModal"
      :module="module"
      :entities="entitySelection"
      :value="tags"
    />
  </div>
</template>

<script>
import { getEntityPermissionCategory } from '@constants/entities';
import XTagModal from '../../../neurons/popover/TagModal.vue';

export default {
  name: 'XEntityTags',
  components: {
    XTagModal,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    entityId: {
      type: String,
      required: true,
    },
    tags: {
      type: Array,
      required: true,
    },
  },
  computed: {
    entitySelection() {
      return {
        ids: [this.entityId],
        include: true,
      };
    },
    userCannotEditDevices() {
      return this.$cannot(getEntityPermissionCategory(this.module),
        this.$permissionConsts.actions.Update);
    },
  },
  methods: {
    removeTag(tag) {
      if (!this.$refs || !this.$refs.tagModal) return;
      this.$refs.tagModal.removeEntitiesLabels([tag]);
    },
    activateTag() {
      if (!this.$refs || !this.$refs.tagModal) return;
      this.$refs.tagModal.activate();
    },
  },
};
</script>

<style lang="scss">
  .x-entity-tags {

    .tag-edit {
      margin-bottom: 24px;
    }

    .tag-list {
      display: grid;
      grid-row-gap: 12px;
      align-items: center;
      grid-template-columns: 2fr 1fr;
      margin-left: 12px;
    }
  }
</style>
