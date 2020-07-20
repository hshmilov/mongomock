<template>
  <div>
    <AModal
      :visible="isActive"
      :cancel-button-props="{ props: { type: 'link' } }"
      :closable="false"
      :centered="true"
      @cancel="closeEnforceModal"
    >
      <div class="enforce-modal-body">
        <div class="mb-8">
          There are {{ selectionCount }} {{ module }} selected. Select the Enforcement Set:
        </div>
        <XSelect
          v-model="selectedEnforcement"
          :options="enforcementOptions"
        />
      </div>
      <template #footer>
        <XButton
          type="link"
          @click="closeEnforceModal"
        >
          Cancel
        </XButton>
        <XButton
          type="primary"
          @click="runEnforcement"
        >
          Run
        </XButton>
      </template>
    </AModal>
    <XEnforcementActionResult
      v-if="showEnforcementActionResult"
      :enforcement-action-to-run="enforceEntities"
      :enforcement-name="selectedEnforcement"
      @close-result="closeEnforcementActionResult"
    />
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex';
import actionModal from '@mixins/action_modal';
import XEnforcementActionResult from '@networks/entities/EnforcementActionResult.vue';
import { Modal } from 'ant-design-vue';
import { ENFORCE_DATA, FETCH_DATA_CONTENT } from '@store/actions';
import XSelect from '@axons/inputs/select/Select.vue';
import XButton from '@axons/inputs/Button.vue';

export default {
  name: 'XEnforceModal',
  components: {
    XSelect,
    XEnforcementActionResult,
    AModal: Modal,
    XButton,
  },
  mixins: [actionModal],
  data() {
    return {
      selectedEnforcement: '',
      showEnforcementActionResult: false,
    };
  },
  computed: {
    ...mapState({
      enforcementOptions(state) {
        return state.enforcements.content.data.map((enforcement) => ({
          name: enforcement.name, title: enforcement.name,
        }));
      },
      view(state) {
        return state[this.module].view;
      },
    }),
  },
  mounted() {
    if (!this.enforcementOptions.length) {
      this.fetchContent({
        module: 'enforcements',
        getCount: false,
      });
    }
  },
  methods: {
    ...mapActions(
      {
        enforceData: ENFORCE_DATA,
        fetchContent: FETCH_DATA_CONTENT,
      },
    ),
    enforceEntities() {
      const { fields, sort, colFilters } = this.view;
      return this.enforceData({
        module: this.module,
        data: {
          name: this.selectedEnforcement,
          view: { fields, sort, colFilters },
          selection: { ...this.entities },
        },
      });
    },
    runEnforcement() {
      this.closeEnforceModal();
      this.showEnforcementActionResult = true;
    },
    closeEnforceModal() {
      this.isActive = false;
    },
    closeEnforcementActionResult() {
      this.showEnforcementActionResult = false;
      this.$emit('done');
    },
  },
};
</script>

<style lang="scss">
  .enforce-modal-body {
    min-height: 120px;
    padding: 24px 24px 0;
    margin-bottom: 24px;
  }
</style>
