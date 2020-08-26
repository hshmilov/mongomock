<template>
  <div class="x-entity-advanced">
    <template v-if="loading">
      <div class="v-spinner-bg" />
      <PulseLoader
        :loading="loading"
        color="#FF7D46"
      />
    </template>
    <XTable
      v-if="getMergedData().length > 0"
      :title="schema.title"
      :module="stateLocation"
      :fields="fields"
      :static-data="getMergedData()"
    >
      <template
        #search="{ onSearch, tableTitle, tableModule, tableView }"
      >
        <XTableSearchFilters
          :module="tableModule"
          :view="tableView"
          :search-placeholder="tableTitle"
          @search="onSearch"
        />
      </template>
      <template slot="actions">
        <XButton
          type="link"
          @click="exportCSV"
        >Export CSV
        </XButton>
      </template>
    </XTable>
  </div>
</template>

<script>
import {
  mapActions,
  mapMutations,
  mapState,
  mapGetters,
} from 'vuex';
import PulseLoader from 'vue-spinner/src/PulseLoader.vue';

import { FETCH_DATA_CONTENT_CSV } from '@store/actions';
import { SET_MERGED_DATA_BY_ID } from '@store/modules/devices';
import XTableSearchFilters from '@neurons/inputs/TableSearchFilters.vue';
import XTable from '@neurons/data/Table.vue';
import XButton from '@axons/inputs/Button.vue';
import mergedData from '../../../../logic/mergeData';

export default {
  name: 'XEntityAdvanced',
  components: {
    XTable, XButton, PulseLoader, XTableSearchFilters,
  },
  props: {
    index: {
      type: Number,
      required: true,
    },
    module: {
      type: String,
      required: true,
    },
    entityId: {
      type: String,
      required: true,
    },
    schema: {
      type: Object,
      required: true,
    },
    data: {
      type: Array,
      default: () => [],
    },
    sort: {
      type: Object,
      default: () => ({
        field: '', desc: true,
      }),
    },
  },
  data() {
    return {
      searchValue: '',
      loading: false,
    };
  },
  computed: {
    ...mapState({
      hyperlinks(state) {
        const hyperlinks = state[this.module].hyperlinks.data;
        if (!hyperlinks || !hyperlinks.aggregator) {
          return {};
        }
        // eslint-disable-next-line no-eval
        return eval(hyperlinks.aggregator);
      },
    }),
    ...mapGetters(['getMergedDataById']),
    stateLocation() {
      return `${this.module}/current/data/advanced/${this.index}`;
    },
    fields() {
      return this.schema.items.filter((item) => this.isSimpleList(item)
        && this.hasAnyValue(item.name)).map((item) => ({
        ...item,
        hyperlinks: this.hyperlinks[`${this.schema.name}.${item.name}`],
      }));
    },
  },
  methods: {
    ...mapMutations({ setMergedDataById: SET_MERGED_DATA_BY_ID }),
    ...mapActions({
      fetchDataCSV: FETCH_DATA_CONTENT_CSV,
    }),
    getMergedData() {
      if (!this.getMergedDataById(this.entityId, this.schema.name)) {
        this.updateMergedData();
      }
      return this.getMergedDataById(this.entityId, this.schema.name) || [];
    },
    updateMergedData() {
      // ignore this method if it was called and the worker is still working
      if (this.loading) {
        return;
      }
      this.loading = true;
      this.$worker.run(mergedData,
        [this.data, this.schema])
        .then((results) => {
          this.setMergedDataById({ id: this.entityId, schema: this.schema, mergedData: results });
          this.loading = false;
        });
    },
    isEmpty(value) {
      return value === undefined || value === null || value === '';
    },
    hasAnyValue(name) {
      return this.getMergedData().find((currentData) => !this.isEmpty(currentData[name]));
    },
    isSimpleList(schema) {
      return (schema.type !== 'array' || schema.items.type !== 'array');
    },
    exportCSV() {
      this.fetchDataCSV({
        module: this.stateLocation,
        endpoint: `${this.module}/${this.entityId}/${this.schema.name}`,
      });
    },
  },
};
</script>

<style lang="scss">
.x-entity-advanced {
  height: 100%;
}
</style>
