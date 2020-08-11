<template>
    <div class="data-table-container">
        <template slot="content">
            <XTable
                    slot="body"
                    v-bind="adaptersDetailsTable"
            />
        </template>
        <XTableData
                :schema="schema"
                :data="data"
                :sort="sort"
                :filter="filter"
        />
        <XTableData

                :schema="schema"
                :data="data"
                :sort="sort"
                :filter="filter"
        />
    </div>
</template>

<script>
  import XTableData from '@neurons/data/TableData';
  import { Popover } from 'ant-design-vue';
  import XTable from '@axons/tables/Table.vue';

  export default {
    name: 'XEntityPopOver',
    components: {
      XTableData,
      APopover: Popover,
      XTable,
    },
    props: {
      isAdaptersField: {
        type: Boolean,
        default: false,
      },
      adaptersDetailsTable: {
        type: Object,
        default: () => {},
      },
      schema: {
        type: Object,
        default: () => {}
      },
      data: {
        type: Object,
        default: () => {}
      },
      sort: {
        type: Object,
        default: () => ({
          field: '', desc: true,
        }),
      },
      filter: {
        type: Array,
        default: () => [],
      },
    }
  };
</script>

<style scoped>

</style>
