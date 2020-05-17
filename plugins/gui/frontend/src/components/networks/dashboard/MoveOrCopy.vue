<template>
  <AModal
    id="move_or_copy"
    :visible="true"
    class="w-xl"
    title="Move or Copy"
    :cancel-button-props="{ props: { type: 'link' } }"
    :closable="false"
    :width="null"
    :centered="true"
    @cancel="handleDismiss"
  >
    <p>Move to Space</p>
    <p>
      <ASelect
        id="select_space"
        :value="space"
        @change="onChangeSpace"
      >
        <ASelectOption
          v-for="space_option in spaces"
          :key="space_option.uuid"
        >
          {{ space_option.name }}
        </ASelectOption>
      </ASelect>
    </p>

    <p>
      <ACheckbox
        id="create_panel_copy"
        :checked="copy"
        :disabled="isPersonalSpaceSelected"
        @change="onChangeCopy"
      >
        Create a copy
      </ACheckbox>
    </p>

    <template slot="footer">
      <XButton
        type="link"
        @click="handleDismiss"
      >
        Cancel
      </XButton>
      <XButton
        type="primary"
        @click="handleApprove"
      >
        OK
      </XButton>
    </template>
  </AModal>
</template>

<script>
import { mapMutations, mapActions, mapState } from 'vuex';
import _find from 'lodash/find';
import { Modal, Checkbox, Select } from 'ant-design-vue';
import XButton from '../../axons/inputs/Button.vue';
import { MOVE_OR_COPY_TOGGLE, MOVE_PANEL, COPY_PANEL } from '../../../store/modules/dashboard';

export default {
  name: 'XMoveOrCopy',
  components: {
    AModal: Modal,
    ACheckbox: Checkbox,
    ASelect: Select,
    ASelectOption: Select.Option,
    XButton,
  },
  data() {
    return {
      copy: true,
      space: null,
    };
  },
  computed: {
    ...mapState({
      spaces(state) {
        return state.dashboard.spaces.data;
      },
      currentSpace(state) {
        return state.dashboard.currentSpace;
      },
      personalSpace(state) {
        return _find(state.dashboard.spaces.data, (space) => space.type === 'personal');
      },
      currentPanel(state) {
        return state.dashboard.currentPanel;
      },
    }),
    isPersonalSpaceSelected() {
      return this.space === this.personalSpace.uuid;
    },
  },
  mounted() {
    this.space = this.currentSpace;
  },
  methods: {
    ...mapMutations({
      moveOrCopyToggle: MOVE_OR_COPY_TOGGLE,
    }),
    ...mapActions({
      movePanel: MOVE_PANEL,
      copyPanel: COPY_PANEL,
    }),
    onChangeCopy() {
      this.copy = !this.copy;
    },
    onChangeSpace(space) {
      this.space = space;
      if (this.isPersonalSpaceSelected) {
        this.copy = true;
      }
    },
    handleApprove() {
      if (this.copy) {
        this.copyPanel({ space: this.space });
      } else {
        this.movePanel({ space: this.space });
      }
      this.handleDismiss();
    },
    handleDismiss() {
      this.moveOrCopyToggle({ active: false });
    },
  },
};
</script>

<style lang="scss">
  #move_or_copy {
    .ant-select {
       width: 200px;
    }
  }
</style>
