<template>
  <div class="x-query-state">
    <div class="header">
      <div
        v-if="enforcement"
        class="title"
      >{{ enforcement.message }}</div>
      <template v-else>
        <div class="title">{{ title }}</div>
        <div
          v-if="!selectedView"
          class="status"
        >[Unsaved]</div>
      </template>
    </div>
    <x-button
      v-if="enforcement"
      link
      @click="navigateFilteredTask"
    >Go to Task</x-button>
    <x-button
      v-else
      id="query_save"
      link
      :disabled="disabled"
      @click="openSaveView"
    >Save as</x-button>
    <x-button
      link
      @click="resetQuery"
    >Reset</x-button>
    <x-historical-date
      v-model="historical"
      :module="module"
    />
    <x-modal
      v-show="saveModal.isActive"
      approve-text="Save"
      approve-id="query_save_confirm"
      size="md"
      @close="closeSaveView"
      @confirm="confirmSaveView"
      @enter="$emit('tour', 'querySaveConfirm')"
      @leave="$emit('tour', 'queryList')"
    >
      <div
        slot="body"
        class="query-save"
      >
        <label for="saveName">Save as:</label>
        <input
          id="saveName"
          v-model="saveModal.name"
          class="flex-expand"
          @keyup.enter="confirmSaveView"
        >
      </div>
    </x-modal>
  </div>
</template>

<script>
  import xButton from '../../../axons/inputs/Button.vue'
  import xHistoricalDate from '../../../neurons/inputs/HistoricalDate.vue'
  import xModal from '../../../axons/popover/Modal.vue'
  import {defaultFields} from '../../../../constants/entities'

  import {mapState, mapMutations, mapActions} from 'vuex'
  import {UPDATE_DATA_VIEW} from '../../../../store/mutations'
  import {SAVE_DATA_VIEW} from '../../../../store/actions'

  export default {
    name: 'XQueryState',
    components: {
      xButton, xHistoricalDate, xModal
    },
    props: {
      module: {
        type: String,
        required: true
      },
      disabled: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        saveModal: {
          isActive: false,
          name: ''
        }
      }
    },
    computed: {
      ...mapState({
        view (state) {
          return state[this.module].view
        },
        allowedDates (state) {
          return state.constants.allowedDates[this.module]
        },
        selectedView (state) {
          let uuid = state[this.module].selectedView
          if (!uuid) return null
          return state[this.module].views.saved.content.data.find(view => view.uuid === uuid)
        }
      }),
      enforcement () {
        return this.view.enforcement
      },
      historical: {
        get () {
          if (!this.view.historical) return ''
          return this.view.historical.substring(0, 10)
        },
        set (newDate) {
          this.updateView({
            module: this.module, view: {
              historical: this.allowedDates[newDate]
            }
          })
        }
      },
      title () {
        if (this.selectedView) {
          return this.selectedView.name
        }
        return 'New Query'
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW
      }),
      ...mapActions({
        saveView: SAVE_DATA_VIEW
      }),
      resetQuery () {
        this.updateView({
          module: this.module, view: {
            enforcement: null,
            query: {
              filter: '', expressions: [], search: ''
            },
            sort: {
              field: '', desc: true
            },
            fields: defaultFields[this.module]
          },
          uuid: null
        })
      },
      navigateFilteredTask() {
        this.$router.push({path: `/enforcements/tasks/${this.enforcement.id}`})
      },
      openSaveView () {
        this.saveModal.isActive = true
      },
      closeSaveView () {
        this.saveModal.isActive = false
      },
      confirmSaveView () {
        if (!this.saveModal.name) return

        this.saveView({
          module: this.module,
          name: this.saveModal.name
        }).then(() => this.saveModal.isActive = false)
      }
    }
  }
</script>

<style lang="scss">
    .x-query-state {
        display: flex;
        width: 100%;
        align-items: center;
        .header {
            display: flex;
            line-height: 28px;
            margin-bottom: 8px;
            .title {
                font-size: 16px;
                font-weight: 400;
                margin-right: 8px;
            }
            .status {
                color: $grey-3;
            }
        }
        .x-button {
            margin-bottom: 8px;
        }
    }
</style>