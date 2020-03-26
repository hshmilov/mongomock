<template>
  <XModal
    :active="true"
    title="Move or Copy"
    @approve="ok"
    @dismiss="close"
  >
    <p>Move to Space</p>
    <p>
      <ASelect
        id="select_space"
        :value="space"
        style="width: 200px"
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
        @change="onChangeCopy"
      >
        Create a copy
      </ACheckbox>
    </p>
  </XModal>
</template>


<script>
import { mapMutations, mapActions, mapState } from 'vuex';
import XModal from '../../axons/popover/Modal.vue';

export default {
  name: 'XMoveOrCopy',
  components: {
    XModal,
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
    }),
  },
  methods: {
    ...mapMutations(['moveOrCopyToggle']),
    ...mapActions(['moveOrCopy']),
    onChangeCopy() {
      this.copy = !this.copy;
    },
    onChangeSpace(space) {
      this.space = space;
    },
    ok() {
      if (!this.space) {
        this.space = this.currentSpace;
      }
      this.moveOrCopy({
        space: this.space,
        copy: this.copy,
      });
      this.close();
    },
    close() {
      this.moveOrCopyToggle(false);
    },
  },
  mounted() {
    this.space = this.currentSpace;
  },
};
</script>

<style lang="scss">
</style>
