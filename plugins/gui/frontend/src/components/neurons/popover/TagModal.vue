<template>
  <x-feedback-modal
    v-model="isActive"
    :handle-save="saveTags"
    :message="`Tagged ${taggedCount} ${module}!`"
    class="x-tag-modal"
  >
    <div v-if="!entities.include" class="tag-modal-info">
      <svg-icon name="symbol/info" :original="true" height="16" />
      With all {{module}} selected, you can add new tags but cannot remove existing ones.
    </div>
    <x-select-box
      v-model="selected"
      :items="labels"
      :indeterminate.sync="indeterminate"
      :multiple="true"
      :keep-open="true"
      :max-chips-to-display="6"
      search-placeholder="Add or Search tags"
    ></x-select-box>
  </x-feedback-modal>
</template>

<script>
import xFeedbackModal from "./FeedbackModal.vue"
import xSelectBox from "../../axons/inputs/select/SelectBox.vue"

import _flatten from 'lodash/flatten'
import _uniq from 'lodash/uniq'
import _intersection from 'lodash/intersection'

import { mapState, mapActions } from "vuex";
import {
  FETCH_DATA_LABELS,
  ADD_DATA_LABELS,
  REMOVE_DATA_LABELS
} from "../../../store/actions";
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from "../../../store/modules/onboarding"
import { TAG_DEVICE } from "../../../constants/getting-started"

export default {
  name: "XTagModal",
  components: { xFeedbackModal, xSelectBox },
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
      default: ""
    }
  },
  data() {
    return {
      isActive: false,
      selected: [],
      taggedCount: 0,
      newItems: [],
      indeterminate: []
    }
  },
  computed: {
    ...mapState({
      labels(state) {
        return state[this.module].labels.data || []
      }
    }),
    initialSelection() {
      if (this.value) {
        return this.value
      }
      return _intersection(...Object.values(this.entitiesMeta))
    },
    initialIndeterminate() {
      if (!this.entitiesMeta) return []
      let labelSets = Object.values(this.entitiesMeta)
      if (!labelSets.length) return []
      return _uniq(_flatten(labelSets.map(labelSet => {
        return labelSet.filter(label => !this.initialSelection.includes(label))
      })))
    }
  },
  methods: {
    ...mapActions({
      fetchLabels: FETCH_DATA_LABELS,
      addLabels: ADD_DATA_LABELS,
      removeLabels: REMOVE_DATA_LABELS,
      milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION
    }),
    activate() {
      this.isActive = true;
      this.selected = [...this.initialSelection]
      this.indeterminate = [...this.initialIndeterminate]
    },
    saveTags() {
      /* Separate added and removed tags and create an uber promise returning after both are updated */
      let added = this.selected.filter(tag => {
        return !this.initialSelection.includes(tag);
      });
      let removed = this.initialSelection.filter(tag => {
        return !this.selected.includes(tag);
      });
      removed.push(...this.initialIndeterminate.filter(item => {
        return (!this.indeterminate.includes(item) && !this.selected.includes(item))
      }))
      return Promise.all([
        this.addLabels({
          module: this.module,
          data: {
            entities: this.entities,
            labels: added
          }
        }),
        this.removeLabels({
          module: this.module,
          data: {
            entities: this.entities,
            labels: removed
          }
        })
      ]).then(response => {
        if (!response || !response.length || (!response[0] && !response[1]))
          return;
        this.taggedCount = response[0] ? response[0].data : response[1].data;
        this.milestoneCompleted({ milestoneName: TAG_DEVICE });
        this.$emit("done");
      });
    },
    removeEntitiesLabels(labels) {
      this.removeLabels({
        module: this.module,
        data: { entities: this.entities, labels }
      });
    }
  },
  created() {
    this.fetchLabels({ module: this.module });
  }
};
</script>

<style lang="scss">
.x-tag-modal {
  .modal-container.w-xl {
    height: 600px;
  }
  .modal-container .modal-body {
    padding: 0;
    margin-bottom: 24px;
    height: 90%;
  }

  .tag-modal-info {
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