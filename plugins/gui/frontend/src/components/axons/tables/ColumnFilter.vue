<template>
  <AModal
    id="column_filter"
    :visible="true"
    :closable="false"
    width="770px"
    :centered="true"
    title="Column Filter"
    @cancel="handleDismiss"
  >
    <span>Show only values:</span>
    <div
      ref="rows"
      class="filters"
    >
      <div
        v-for="(filter, index) in unsavedFilters"
        :key="index"
        class="filter"
      >
        <XButton
          class="include"
          :on="!filter.include"
          @click="toggleInclude(index)"
        >
          NOT
        </XButton>
        <AInput
          v-model="filter.term"
          placeholder="CONTAINS (OR EMPTY FOR ALL VALUES)"
          @keyup.enter="handleApprove"
        />
        <XButton
          class="remove"
          type="link"
          icon="close"
          @click="removeFilter(index)"
        />
      </div>
    </div>

    <XButton
      class="addFilter"
      @click="addFilter"
    >
      +
    </XButton>


    <template slot="footer">
      <XButton
        class="clear"
        type="link"
        @click="clearFilters"
      >
        Clear
      </XButton>
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
import { mapMutations } from 'vuex';
import { Modal, Input } from 'ant-design-vue';
import XButton from '@axons/inputs/Button.vue';
import { UPDATE_DATA_VIEW_FILTER } from '@store/mutations';
import _cloneDeep from 'lodash/cloneDeep';

export default {
  name: 'XColumnFilter',
  components: {
    XButton,
    AInput: Input,
    AModal: Modal,
  },
  props: {
    filterColumnName: {
      type: String,
      default: '',
    },
    savedFilters: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      defaultFilter: { include: true, term: '' },
      unsavedFilters: [],
      visible: false,
    };
  },
  mounted() {
    this.resetFilters();
    this.focusLastFilter();
  },
  methods: {
    ...mapMutations({
      updateViewFilter: UPDATE_DATA_VIEW_FILTER,
    }),
    toggleInclude(index) {
      this.unsavedFilters[index].include = !this.unsavedFilters[index].include;
    },
    getDefaultFilter() {
      return { ...this.defaultFilter };
    },
    addFilter() {
      this.unsavedFilters.push(this.getDefaultFilter());
      this.$nextTick(() => {
        const ref = this.$refs.rows;
        ref.scrollTop = ref.scrollHeight;
      });
      this.focusLastFilter();
    },
    resetFilters() {
      this.unsavedFilters = _cloneDeep(this.savedFilters);
      if (this.unsavedFilters.length === 0) {
        this.clearFilters();
      }
    },
    clearFilters() {
      this.unsavedFilters = [this.getDefaultFilter()];
    },
    removeFilter(index) {
      this.unsavedFilters.splice(index, 1);
      if (this.unsavedFilters.length === 0) {
        this.clearFilters();
      }
    },
    handleApprove() {
      const filters = this.unsavedFilters.filter((f) => f.term.trim() !== '' || !f.include);
      this.$emit('updateColFilters',
        {
          filters,
          fieldName: this.filterColumnName,
        });
      this.handleDismiss();
    },
    handleDismiss() {
      this.$emit('toggleColumnFilter');
    },
    focusLastFilter() {
      this.$nextTick(() => {
        const ref = this.$refs.rows;
        ref.querySelector('.filter:last-child input').focus();
      });
    },
  },
};
</script>

<style lang="scss">
  #column_filter {
    --filter-row-height: 40px;
    > div {
      padding: 12px;
    }
    input {
      margin-left: 5px;
    }
    .filter {
      padding: 5px 0 5px 5px;
      display: flex;
      height: var(--filter-row-height);
      .x-button.include {
        background: $theme-white;
        color: $theme-black;
        height: 30px;
        padding: 6px 2px;
        font-weight: 200;
        font-size: 12px;
        width: 30px;

        &.on {
          background-color: $theme-black;
          color: $grey-2;
          border-color: $theme-black;
        }
      }
    }
    .filters {
      max-height: calc(var(--filter-row-height) * 5);
      overflow: auto;
      margin: 11px 0 7px -5px;
      @include  y-scrollbar;
    }

    .addFilter {
      width: 30px;
      padding: 0;
    }

    .ant-modal-footer {
      display: flex;
      margin-top: 26px;
      .clear {
        margin-right: auto;
        padding: 0 8px;
      }
    }

  }
</style>
