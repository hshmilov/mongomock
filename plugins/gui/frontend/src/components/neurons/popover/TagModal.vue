<template>
  <XFeedbackModal
    v-model="isActive"
    :handle-save="saveTags"
    :message="`Tagged ${taggedCount} ${module}!`"
    class="x-tag-modal"
  >
    <div
      v-if="!entities.include"
      class="tag-modal-info"
    >
      <XIcon
        family="symbol"
        type="info"
      />
      With all {{ module }} selected, you can add new tags but cannot remove existing ones.
    </div>
    <VRow>
      <VCol cols="12">
        <XCombobox
          v-model="selected"
          :items="labels"
          :indeterminate.sync="indeterminate"
          multiple
          keep-open
        />
      </VCol>
    </VRow>
  </XFeedbackModal>
</template>

<script>

import _flatten from 'lodash/flatten';
import _uniq from 'lodash/uniq';
import _intersection from 'lodash/intersection';

import { mapState, mapActions } from 'vuex';
import XIcon from '@axons/icons/Icon';
import XCombobox from '../../axons/inputs/combobox/index.vue';
import XFeedbackModal from './FeedbackModal.vue';
import {
  FETCH_DATA_LABELS,
  ADD_DATA_LABELS,
  REMOVE_DATA_LABELS,
} from '../../../store/actions';
import { SET_GETTING_STARTED_MILESTONE_COMPLETION } from '../../../store/modules/onboarding';
import { TAG_DEVICE } from '../../../constants/getting-started';

export default {
  name: 'XTagModal',
  components: { XFeedbackModal, XCombobox, XIcon },
  props: {
    module: {
      type: String,
      required: true,
    },
    entities: {
      type: Object,
      required: true,
    },
    entitiesMeta: {
      type: Object,
      default: () => {},
    },
    value: {
      type: Array,
      default: undefined,
    },
    title: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      isActive: false,
      selected: [],
      taggedCount: 0,
      newItems: [],
      indeterminate: [],
    };
  },
  computed: {
    ...mapState({
      labels(state) {
        const res = state[this.module].labels.data || [];
        return res.map((i) => i.name);
      },
    }),
    initialSelection() {
      if (this.value) {
        return this.value.map((i) => (i.name ? i.name : i));
      }
      return _intersection(...Object.values(this.entitiesMeta));
    },
    initialIndeterminate() {
      if (!this.entitiesMeta) return [];
      const labelSets = Object.values(this.entitiesMeta);
      if (!labelSets.length) return [];
      return _uniq(_flatten(labelSets.map((labelSet) => labelSet.filter((label) => !this.initialSelection.includes(label)))));
    },
  },
  methods: {
    ...mapActions({
      fetchLabels: FETCH_DATA_LABELS,
      addLabels: ADD_DATA_LABELS,
      removeLabels: REMOVE_DATA_LABELS,
      milestoneCompleted: SET_GETTING_STARTED_MILESTONE_COMPLETION,
    }),
    activate() {
      this.isActive = true;
      this.selected = [...this.initialSelection];
      this.indeterminate = [...this.initialIndeterminate];
    },
    async saveTags() {
      /* Separate added and removed tags */
      const added = this.selected.filter((tag) => !this.initialSelection.includes(tag));
      const removed = this.initialSelection.filter((tag) => !this.selected.includes(tag));
      removed.push(...this.initialIndeterminate.filter((item) => (!this.indeterminate.includes(item) && !this.selected.includes(item))));

      const addResponse = await this.addLabels({
        module: this.module,
        data: {
          entities: this.entities,
          labels: added,
        },
      });

      const removeResponse = await this.removeLabels({
        module: this.module,
        data: {
          entities: this.entities,
          labels: removed,
        },
      });

      if (!addResponse && !removeResponse) return;
      this.taggedCount = addResponse ? addResponse.data : removeResponse.data;
      this.milestoneCompleted({ milestoneName: TAG_DEVICE });
      this.$emit('done');
    },
    removeEntitiesLabels(labels) {
      this.removeLabels({
        module: this.module,
        data: { entities: this.entities, labels },
      });
    },
  },
  created() {
    this.fetchLabels({ module: this.module });
  },
};
</script>

<style lang="scss">
.x-tag-modal {
  .modal-container .modal-body {
    padding: 0;
    margin: 24px 0;
    height: 90%;

    .row {
      /* fix content overflow x caused by vuetify .row default side margins */
      margin-left: 0px;
      margin-right: 0px;
    }
  }

  .tag-modal-info {
    padding: 8px;
    display: flex;
    align-items: center;
    .x-icon {
      font-size: 16px;
      margin-right: 4px;
    }
  }

  .x-checkbox {
    flex-basis: 50%;
  }
}
</style>
