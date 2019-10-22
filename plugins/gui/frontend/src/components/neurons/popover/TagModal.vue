<template>
  <x-feedback-modal
    v-model="isActive"
    :handle-save="saveTags"
    :message="`Tagged ${taggedCount} ${module}!`"
    class="x-tag-modal"
    @enter="onEnter"
  >
    <div
      v-if="!entities.include"
      class="tag-modal-info"
    >
      <svg-icon name="symbol/info" :original="true" height="16"
      />With all {{module}} selected, you can add new tags but cannot remove existing ones.</div>
    <x-search-input
      ref="searchInput"
      v-model="searchValue"
      tabindex="1"
    />
    <x-checkbox-list
      v-model="selected"
      :items="currentLabels"
    />
  </x-feedback-modal>
</template>

<script>
  import xFeedbackModal from './FeedbackModal.vue'
  import xSearchInput from '../inputs/SearchInput.vue'
  import xCheckboxList from '../inputs/CheckboxList.vue'

  import { mapState, mapActions } from 'vuex'
  import {
    FETCH_DATA_LABELS, ADD_DATA_LABELS, REMOVE_DATA_LABELS
  } from '../../../store/actions'
  import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../../store/modules/onboarding';
  import { TAG_DEVICE } from '../../../constants/getting-started'

  export default {
    name: 'XTagModal',
    components: { xFeedbackModal, xSearchInput, xCheckboxList },
    props: {
      module: {
        type: String,
        required: true
      },
      entities: {
        type: Object,
        required: true
      },
      entitiesMeta: {
        type: Object,
        default: () => {}
      },
      value: {
        type: Array,
        default: undefined
      },
      title: {
        type: String,
        default: ''
      }
    },
    computed: {
      ...mapState({
        labels (state) {
          const labels = state[this.module].labels.data
          return labels ? labels.sort() : []
        }
      }),
      initialSelection () {
        if (this.value) return this.value
        let labelSets = Object.values(this.entitiesMeta)
        if (!labelSets.length) return []
        return labelSets[0].filter(label => labelSets.slice(1)
                .reduce((exists, set) => exists && set && set.includes(label), true)
        )
      },
      currentLabels () {
        if (!this.searchValue) return this.labels
        let matchingLabels = this.labels.filter((label) => {
          return label.name.toLowerCase().includes(this.searchValue.toLowerCase())
        })
        if (!matchingLabels.length || matchingLabels[0].name !== this.searchValue) {
          matchingLabels.unshift({ name: this.searchValue, title: `${this.searchValue} (new)` })
        }
        return matchingLabels
      }
    },
    data () {
      return {
        isActive: false,
        selected: [],
        searchValue: '',
        taggedCount: 0
      }
    },
    methods: {
      ...mapActions({
        fetchLabels: FETCH_DATA_LABELS, addLabels: ADD_DATA_LABELS, 
        removeLabels: REMOVE_DATA_LABELS,
        milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION
      }),
      activate () {
        this.isActive = true
        this.selected = [ ...this.initialSelection ]
      },
      onEnter () {
        if (!this.$refs.searchInput) return
        this.$refs.searchInput.focus()
      },
      saveTags () {
        /* Separate added and removed tags and create an uber promise returning after both are updated */
        let added = this.selected.filter((tag) => {
          return (!this.initialSelection.includes(tag))
        })
        let removed = this.initialSelection.filter((tag) => {
          return (!this.selected.includes(tag))
        })
        this.searchValue = ''
        return Promise.all([
          this.addLabels({
            module: this.module, data: {
              entities: this.entities, labels: added
            }
          }),
          this.removeLabels({
            module: this.module, data: {
              entities: this.entities, labels: removed
            }
          })
        ]).then(response => {
          if (!response || !response.length || (!response[0] && !response[1])) return
          this.taggedCount = response[0] ? response[0].data : response[1].data
          this.milestoneCompleted({ milestoneName: TAG_DEVICE })
          this.$emit('done')
        })
      },
      removeEntitiesLabels (labels) {
        this.removeLabels({
          module: this.module, data: { entities: this.entities, labels }
        })
      }
    },
    created () {
      this.fetchLabels({ module: this.module })
    }
  }
</script>

<style lang="scss">
    .x-tag-modal {

        .x-search-input {
            width: 50%;
        }

        .tag-modal-info {
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            .svg-icon {
              margin-right: 4px;
            }
        }

        .x-checkbox {
            flex-basis: 50%;
        }
    }
</style>