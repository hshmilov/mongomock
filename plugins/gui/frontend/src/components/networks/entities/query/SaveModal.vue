<template>
  <x-modal
    approve-text="Save"
    approve-id="query_save_confirm"
    size="md"
    class="x-save-modal"
    :disabled="!name"
    @close="close"
    @confirm="confirmSave"
    @enter="$emit('enter')"
  >
    <div
      slot="body"
      class="query-name"
    >
      <label for="saveName">
        <template v-if="isEdit">Rename:</template>
        <template v-else>Save as:</template>
      </label>
      <input
        id="saveName"
        v-model="name"
        class="name-input"
        @keyup.enter="confirmSave"
      >
    </div>
  </x-modal>
</template>

<script>
  import xModal from '../../../axons/popover/Modal.vue'

  import {mapActions} from 'vuex'
  import {SAVE_DATA_VIEW} from '../../../../store/actions'

  export default {
    name: 'XSaveModal',
    components: {
      xModal
    },
    props: {
      module: {
        type: String,
        required: true
      },
      view: {
        type: Object,
        default: null
      }
    },
    data () {
      return {
        name: ''
      }
    },
    computed: {
      isEdit () {
        return Boolean(this.view)
      }
    },
    created () {
      if (this.view) {
        this.name = this.view.name
      }
    },
    methods: {
      ...mapActions({
        saveView: SAVE_DATA_VIEW
      }),
      close () {
        this.$emit('close')
      },
      confirmSave () {
        if (!this.name) return

        this.saveView({
          module: this.module,
          name: this.name,
          uuid: this.isEdit? this.view.uuid : null
        }).then(() => this.close())
      }
    }
  }
</script>

<style lang="scss">
  .x-save-modal {
    .query-name {
      display: flex;
      align-items: center;
      .name-input {
        flex: 1 0 auto;
        margin-left: 8px;
      }
    }
  }
</style>