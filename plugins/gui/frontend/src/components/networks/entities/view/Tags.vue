<template>
  <div class="x-entity-tags">
    <div class="tag-edit">
      <x-button
        link
        :disabled="readOnly"
        @click="activateTag"
      >Edit Tags</x-button>
    </div>
    <div class="tag-list w-lg">
      <template v-for="(tag, i) in tags">
        <div :key="i">
          <md-chip class="tag">{{ tag }}</md-chip>
        </div>
        <x-button
          :key="tag"
          link
          :disabled="readOnly"
          @click="removeTag(tag)"
        >Remove</x-button>
      </template>
    </div>
    <x-tag-modal
      ref="tagModal"
      :module="module"
      :entities="entitySelection"
      :value="tags"
    />
  </div>
</template>

<script>
  import xButton from '../../../axons/inputs/Button.vue'
  import xTagModal from '../../../neurons/popover/TagModal.vue'

  export default {
    name: 'XEntityTags',
    components: {
      xButton, xTagModal
    },
    props: {
      module: {
        type: String,
        required: true
      },
      entityId: {
        type: String,
        required: true
      },
      tags: {
        type: Array,
        required: true
      },
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    computed: {
      entitySelection () {
        return {
          ids: [this.entityId],
          include: true
        }
      }
    },
    methods: {
      removeTag (tag) {
        if (!this.$refs || !this.$refs.tagModal) return
        this.$refs.tagModal.removeEntitiesLabels([tag])
      },
      activateTag () {
        if (!this.$refs || !this.$refs.tagModal) return
        this.$refs.tagModal.activate()
      }
    }
  }
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