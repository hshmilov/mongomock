<template>
  <XTabs
    v-if="basic && basicSchema"
    :vertical="true"
    class="x-entity-general"
  >
    <XTab
      id="basic"
      key="basic"
      title="Basic Info"
      :selected="true"
    >
      <XList
        :data="basic"
        :schema="basicSchema"
      />
    </XTab>
    <XTab
      v-for="(item, i) in advancedSorted"
      :id="item.schema.name"
      :key="item.schema.name"
      :title="item.schema.title"
    >
      <XEntityAdvanced
        :index="i"
        :module="module"
        :entity-id="entityId"
        :schema="item.schema"
        :data="item.data"
        :sort="item.view.sort"
      />
    </XTab>
  </XTabs>
</template>

<script>
import _sortBy from 'lodash/sortBy';
import { mapState } from 'vuex';
import XTabs from '../../../axons/tabs/Tabs.vue';
import XTab from '../../../axons/tabs/Tab.vue';
import XList from '../../../neurons/schema/List.vue';
import XEntityAdvanced from './Advanced.vue';


export default {
  name: 'XEntityGeneral',
  components: {
    XTabs, XTab, XList, XEntityAdvanced,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    entityId: {
      type: String,
      required: true,
    },
    basic: {
      type: Object,
      default: () => ({}),
    },
    advanced: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      excludedFields: ['specific_data.data.correlation_reasons'],
    };
  },
  computed: {
    ...mapState({
      fields(state) {
        return state[this.module].fields.data;
      },
      hyperlinks(state) {
        const hyperlinks = state[this.module].hyperlinks.data;
        if (!hyperlinks || !hyperlinks.aggregator) {
          return {};
        }
        return eval(hyperlinks.aggregator);
      },
    }),
    advancedSorted() {
      return _sortBy(this.advanced, (item) => item.schema.name);
    },
    schemaGenericFields() {
      return this.fields.generic.filter(
        (item) => !this.excludedFields.includes(item.name),
      );
    },
    basicSchema() {
      if (!this.fields.generic) return null;
      const items = this.$isAxoniusUser() ? this.fields.generic : this.schemaGenericFields;
      return {
        type: 'array',
        items,
        hyperlinks: this.hyperlinks,
      };
    },
  },
};
</script>

<style lang="scss">
  .x-entity-general {

    > .body {
      padding: 0 12px;
    }

    .x-data-table {
      height: 100%;

      .table-header {
        background: $theme-white;
      }

      .x-pages {
        background-color: $grey-0;
        border-color: $grey-0;

        &:after {
          border-left-color: $grey-0;
        }

      }
    }
  }
</style>
