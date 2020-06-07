<template>
  <XPage
    title="Activity Logs"
    class="x-audit"
  >
    <XTable
      module="audit"
      endpoint="settings/audit"
      title="Items"
      :fields="fields"
      :searchable="true"
    >
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
import XPage from '../axons/layout/Page.vue';
import XTable from '../neurons/data/Table.vue';
import XButton from '../axons/inputs/Button.vue';


export default {
  name: 'XAudit',
  components: {
    XPage, XTable, XButton, AIcon: Icon,
  },
  data() {
    return {
      fields: [{
        name: 'type',
        title: 'Type',
        type: 'string',
        format: 'icon',
      }, {
        name: 'date',
        title: 'Date',
        type: 'string',
        format: 'date-time',
      }, {
        name: 'user',
        title: 'User',
        type: 'string',
      }, {
        name: 'action',
        title: 'Action',
        type: 'string',
      }, {
        name: 'category',
        title: 'Category',
        type: 'string',
      }, {
        name: 'message',
        title: 'Message',
        type: 'string',
      }],
      exportTableInProgress: false,
    };
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
