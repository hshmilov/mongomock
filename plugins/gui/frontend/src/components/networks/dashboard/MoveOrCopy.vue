<template>
  <AModal
    id="move_or_copy"
    :visible="true"
    class="w-xl"
    title="Move or Copy"
    :closable="false"
    :width="null"
    :centered="true"
    @cancel="handleDismiss"
  >
    <p>Move to space</p>
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
        :disabled="cannotCopy || cannotMove || isPersonalSpaceSelected"
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
import {
  mapActions, mapState, mapGetters,
} from 'vuex';
import _find from 'lodash/find';
import { Modal, Checkbox, Select } from 'ant-design-vue';
import _some from 'lodash/some';
import _flow from 'lodash/flow';
import _get from 'lodash/get';
import viewsMixin from '../../../mixins/views';
import { MOVE_PANEL, COPY_PANEL } from '../../../store/modules/dashboard';
import { ChartViewGetter } from '../../../constants/utils';
import { SpaceTypesEnum } from '../../../constants/dashboard';

export default {
  name: 'XMoveOrCopy',
  components: {
    AModal: Modal,
    ACheckbox: Checkbox,
    ASelect: Select,
    ASelectOption: Select.Option,
  },
  mixins: [viewsMixin],
  props: {
    currentPanel: {
      type: Object,
      required: true,
    },
    currentSpace: {
      type: String,
      required: true,
    },
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
        const isQueryPrivate = (query) => {
          const savedQuery = this.getSavedQueryById(query.id, query.entity);
          return savedQuery && savedQuery.private;
        };
        const chartHasPrivateQuery = (chart) => _some(ChartViewGetter(chart),
          (query) => isQueryPrivate(query));

        const spacesData = _get(state, 'dashboard.spaces.data', []);
        return _flow([
          (spaces) => (this.cannotCopy
            ? spaces.filter((space) => space.type !== SpaceTypesEnum.personal) : spaces),
          (spaces) => (chartHasPrivateQuery(this.currentPanel)
            ? spaces.filter((space) => space.uuid === this.currentSpace) : spaces),
        ])(spacesData);
      },
      personalSpace(state) {
        return _find(state.dashboard.spaces.data,
          (space) => space.type === SpaceTypesEnum.personal);
      },
    }),
    ...mapGetters({
      getSavedQueryById: 'getSavedQueryById',
    }),
    cannotCopy() {
      return this.$cannot(this.$permissionConsts.categories.Dashboard,
        this.$permissionConsts.actions.Add, this.$permissionConsts.categories.Charts);
    },
    cannotMove() {
      return !this.cannotCopy
        && this.$cannot(this.$permissionConsts.categories.Dashboard,
          this.$permissionConsts.actions.Update, this.$permissionConsts.categories.Charts);
    },
    isPersonalSpaceSelected() {
      return this.space === this.personalSpace.uuid;
    },
  },
  mounted() {
    this.space = this.currentSpace;
    if (this.cannotCopy) {
      this.copy = false;
    } else if (this.cannotMove) {
      this.copy = true;
    }
  },
  methods: {
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
    async handleApprove() {
      if (this.copy) {
        const res = await this.copyPanel({ space: this.space, chart: { ...this.currentPanel, name: `COPY - ${this.currentPanel.name}` } });
        if (this.space === this.currentSpace) {
          this.$emit('duplicate', res.data);
        }
      } else {
        const moveToCurrentSpace = (this.space === this.currentSpace) && !this.copy;
        if (moveToCurrentSpace) return;
        const { uuid } = this.currentPanel;
        await this.movePanel({ space: this.space, uuid });
        this.$emit('moved', uuid);
      }
      this.handleDismiss();
    },
    handleDismiss() {
      this.$emit('close');
    },
  },
};
</script>

<style lang="scss">
  #move_or_copy {
    .ant-select {
       width: 360px;
    }
  }
</style>
