<template>
  <x-tabs
    v-if="basic && basicSchema"
    :vertical="true"
    class="x-entity-general"
  >
    <x-tab
      id="basic"
      key="basic"
      title="Basic Info"
      :selected="true"
    >
      <x-list
        :data="basic"
        :schema="basicSchema"
      />
    </x-tab>
    <x-tab
      v-for="(item, i) in advanced"
      :id="item.schema.name"
      :key="item.schema.name"
      :title="item.schema.title"
    >
      <x-entity-advanced
        :index="i"
        :module="module"
        :entity-id="entityId"
        :schema="item.schema"
        :data="item.data"
        :sort="item.view.sort"
      />
    </x-tab>
  </x-tabs>
</template>

<script>
  import xTabs from '../../../axons/tabs/Tabs.vue'
  import xTab from '../../../axons/tabs/Tab.vue'
  import xList from '../../../neurons/schema/List.vue'
  import xEntityAdvanced from './Advanced.vue'

  import {mapState} from 'vuex'


  export default {
    name: 'XEntityGeneral',
    components: {
      xTabs, xTab, xList, xEntityAdvanced
    },
    props: {
      module: {
        type: String,
        required: true
      },
      entityId: {
        type: String,
        required: true
      },
      basic: {
        type: Object,
        default: () => {
          return {}
        }
      },
      advanced: {
        type: Array,
        default: () => []
      }
    },
    computed: {
      ...mapState({
        fields(state) {
          return state[this.module].fields.data
        }
      }),
      basicSchema () {
        if (!this.fields.generic) return null
        return {
          type: 'array',
          items: this.fields.generic
        }
      }
    }
  }
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