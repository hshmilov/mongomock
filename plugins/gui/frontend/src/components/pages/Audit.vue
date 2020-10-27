<template>
  <XPage
    title="Activity Logs"
    class="x-audit"
  >
    <XTable
      module="audit"
      endpoint="settings/audit"
      title="Items"
      :fields="FIELDS"
    >
      <template
        #search="{ onSearch, tableTitle, tableModule, tableView }"
      >
        <XTableSearchFilters
          :module="tableModule"
          :search-placeholder="tableTitle"
          :view="tableView"
          enable-date-search
          @search="onSearch"
        />
      </template>
      <template #actions>
        <XButton
          type="link"
          :disabled="exportTableInProgress"
          @click="exportTableToCSV"
        >
          <template v-if="exportTableInProgress">
            <AIcon type="loading" />Exporting...
          </template>
          <template v-else>Export CSV</template>
        </XButton>
      </template>
    </XTable>
  </XPage>
</template>

<script>
import { mapActions } from 'vuex';
import { FETCH_CSV } from '@store/modules/audit';

import { Icon } from 'ant-design-vue';
import XTableSearchFilters from '@neurons/inputs/TableSearchFilters.vue';
import XPage from '@axons/layout/Page.vue';
import XTable from '@neurons/data/Table.vue';
import { auditFields } from '@constants/audit';

export default {
  name: 'XAudit',
  components: {
    XPage, XTable, AIcon: Icon, XTableSearchFilters,
  },
  data() {
    return {
      exportTableInProgress: false,
    };
  },
  created() {
    this.FIELDS = auditFields;
  },
  methods: {
    ...mapActions({
      fetchCSV: FETCH_CSV,
    }),
    toggleExportProgress() {
      this.exportTableInProgress = !this.exportTableInProgress;
    },
    exportTableToCSV() {
      this.toggleExportProgress();
      this.fetchCSV().then(this.toggleExportProgress);
    },
  },
};
</script>

<style lang="scss">
.x-audit {

  .x-data-table {
    height: 100%;

    .anticon-loading {
      margin-right: 4px;
    }

    .x-table-head {
      min-width: auto;
    }

    .table-td-type {
      width: 30px;
      text-align: left;

      .x-icon {
        margin: unset;
        width: inherit;
        justify-content: center;
      }
    }
  }
}
</style>
