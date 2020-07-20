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
        v-for="(filter, index) in unsavedValueFilters"
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

    <div v-if="enableExcludeAdaptersFilter">

      <div class="exclude-adapter__title">
        Exclude adapter connections:
      </div>

      <ASelect
        v-model="unsavedExcludeAdapters"
        mode="multiple"
        class="exclude-adapter__select"
        placeholder="Select adapters to exclude"
        option-label-prop="label"
        :filter-option="filterOption"
      >
        <ASelectOption
          v-for="a in getConfiguredAdapters"
          :key="a.id"
          :value="a.id"
          :label="a.title"
        >
          <span
            role="img"
            :aria-label="a.title"
            class="exclude-adapter__logo"
          >
            <img
              :src="require(`Logos/adapters/${a.id}.png`)"
              width="24"
            >
          </span>
          {{ a.title }}
        </ASelectOption>
      </ASelect>

    </div>


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
import { mapActions, mapGetters } from 'vuex';
import { Modal, Input, Select } from 'ant-design-vue';
import XButton from '@axons/inputs/Button.vue';
import { FETCH_ADAPTERS } from '@store/modules/adapters';
import _cloneDeep from 'lodash/cloneDeep';

export default {
  name: 'XColumnFilter',
  components: {
    XButton,
    AInput: Input,
    AModal: Modal,
    ASelect: Select,
    ASelectOption: Select.Option,
  },
  props: {
    filterColumnName: {
      type: String,
      default: '',
    },
    enableExcludeAdaptersFilter: {
      type: Boolean,
      default: true,
    },
    savedFilters: {
      type: Array,
      default: () => [],
    },
    savedExcludeAdapters: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      defaultFilter: { include: true, term: '' },
      unsavedValueFilters: [],
      visible: false,
      unsavedExcludeAdapters: [],
    };
  },
  computed: {
    ...mapGetters({
      getConfiguredAdapters: 'getConfiguredAdapters',
    }),
  },
  mounted() {
    this.resetFilters();
    this.focusLastFilter();
  },
  created() {
    this.fetchAdapters();
  },
  methods: {
    ...mapActions({ fetchAdapters: FETCH_ADAPTERS }),
    toggleInclude(index) {
      this.unsavedValueFilters[index].include = !this.unsavedValueFilters[index].include;
    },
    getDefaultFilter() {
      return { ...this.defaultFilter };
    },
    addFilter() {
      this.unsavedValueFilters.push(this.getDefaultFilter());
      this.$nextTick(() => {
        const ref = this.$refs.rows;
        ref.scrollTop = ref.scrollHeight;
      });
      this.focusLastFilter();
    },
    resetFilters() {
      this.unsavedValueFilters = _cloneDeep(this.savedFilters);
      if (this.unsavedValueFilters.length === 0) {
        this.clearValueFilters();
      }
      this.unsavedExcludeAdapters = _cloneDeep(this.savedExcludeAdapters);
      if (this.unsavedExcludeAdapters.length === 0) {
        this.clearExcludedAdapters();
      }
    },
    clearFilters() {
      this.clearValueFilters();
      this.clearExcludedAdapters();
    },
    clearValueFilters() {
      this.unsavedValueFilters = [this.getDefaultFilter()];
    },
    clearExcludedAdapters() {
      this.unsavedExcludeAdapters = [];
    },
    removeFilter(index) {
      this.unsavedValueFilters.splice(index, 1);
      if (this.unsavedValueFilters.length === 0) {
        this.clearValueFilters();
      }
    },
    handleApprove() {
      const filters = this.unsavedValueFilters.filter((f) => f.term.trim() !== '' || !f.include);
      this.$emit('updateColFilters',
        {
          filters,
          excludeAdapters: this.unsavedExcludeAdapters,
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
    filterOption(input, option) {
      return (
        option.componentOptions.propsData.label.toLowerCase().indexOf(input.toLowerCase()) >= 0
      );
    },
  },
};
</script>

<style lang="scss">
  #column_filter {
    --filter-row-height: 40px;

    .exclude-adapter {
      &__title {
        padding: 12px 0;
      }
      &__select {
        width: 100%
      }
      &__logo {
        padding-right: 14px;
      }
    }

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
