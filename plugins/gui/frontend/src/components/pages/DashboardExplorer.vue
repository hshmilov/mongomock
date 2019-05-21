<template>
  <x-page
    :breadcrumbs="[
      { title: 'axonius dashboard', path: { name: 'Dashboard'}},
      { title: 'Search' }
    ]"
  >
    <x-search-insights />
    <div class="explorer-results">
      <x-table
        v-for="entity in entities"
        :key="entity['internal_axon_id']"
        id-field="internal_axon_id"
        :module="entity.name"
        :on-click-row="() => configEntity($event, entity.name)"
      >
        <template slot="actions">
          <x-button
            link
            @click="viewEntities(entity.name)"
          >View in {{ entity.title }}</x-button>
        </template>
      </x-table>
    </div>
  </x-page>

</template>

<script>
  import xPage from '../axons/layout/Page.vue'
  import xSearchInsights from '../neurons/inputs/SearchInsights.vue'
  import xTable from '../neurons/data/Table.vue'
  import xButton from '../axons/inputs/Button.vue'
  import { entities, defaultFields } from '../../constants/entities'

  import { mapMutations } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../store/mutations'

  export default {
    name: 'XDashboardExplorer',
    components: {
      xPage, xSearchInsights, xTable, xButton
    },
    data () {
      return {
        resetFilters: true
      }
    },
    computed: {
      entities () {
        return entities
      }
    },
    beforeDestroy () {
      if (!this.resetFilters) return
      entities.forEach(entity => {
        this.updateDataView({
          module: entity.name, view: {
            query: {
              filter: ''
            }, fields: defaultFields[entity.name]
          }
        })
      })
    },
    methods: {
      ...mapMutations({ updateDataView: UPDATE_DATA_VIEW }),
      configEntity (entityId, entityType) {
        this.$router.push({
          path: `/${entityType}/${entityId}`
        })
      },
      viewEntities (entityType) {
        this.resetFilters = false
        this.$router.push({
          path: `/${entityType}`
        })
      }
    }
  }
</script>

<style lang="scss">
    .explorer-results {
        height: calc(100% - 48px);

        .x-data-table {
            height: 50%;
        }
    }
</style>