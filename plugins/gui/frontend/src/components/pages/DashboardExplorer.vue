<template>
  <XPage
    :breadcrumbs="[
      { title: 'axonius dashboard', path: { name: 'Dashboard'}},
      { title: 'Search' }
    ]"
  >
    <XSearchInsights @search="onSearch" />
    <div class="explorer-results">
      <XTable
        v-for="{name, title} in entities"
        :key="name"
        ref="table"
        :experimental-api="isExperimentalAPI"
        :module="name"
        :fields="defaultFields[name]"
        :view-only="true"
      >
        <template #actions>
          <XButton
            type="link"
            @click="viewEntities(name)"
          >View in {{ title }}</XButton>
        </template>
      </XTable>
    </div>
  </XPage>
</template>

<script>
import { mapState, mapGetters, mapMutations } from 'vuex';
import _get from 'lodash/get';
import XPage from '../axons/layout/Page.vue';
import XSearchInsights from '../neurons/inputs/SearchInsights.vue';
import XTable from '../networks/entities/Table.vue';
import XButton from '../axons/inputs/Button.vue';
import { entities, defaultFieldsExplorer } from '../../constants/entities';
import { EXACT_SEARCH } from '../../store/getters';
import { UPDATE_DATA_VIEW } from '../../store/mutations';

export default {
  name: 'XDashboardExplorer',
  components: {
    XPage, XSearchInsights, XTable, XButton,
  },
  data() {
    return {
      resetFilters: true,
    };
  },
  computed: {
    ...mapState({
      featureFlags(state) {
        return _get(state, 'settings.configurable.gui.FeatureFlags.config', null);
      },
    }),
    ...mapGetters({
      exactSearch: EXACT_SEARCH,
    }),
    entities() {
      return entities.filter((entity) => this.$canViewEntity(entity.name));
    },
    isExperimentalAPI() {
      return !(!this.featureFlags || !this.featureFlags.experimental_api);
    },
    defaultFields() {
      return defaultFieldsExplorer;
    },
  },
  mounted() {
    this.onSearch(this.$route.query.search || '');
  },
  methods: {
    ...mapMutations({
      updateDataView: UPDATE_DATA_VIEW,
    }),
    viewEntities(entityType) {
      this.updateDataView({
        module: entityType,
        view: {
          fields: this.defaultFields[entityType],
        },
      });
      this.$router.push({
        path: `/${entityType}`,
      });
    },
    updateEntitiesPerTable() {
      this.$refs.table.forEach((ref) => ref.updateEntities());
    },
    onSearch(search) {
      const expressions = search.split(',').map((exp) => exp.trim()).filter((exp) => exp);
      this.entities.forEach(({ name }) => {
        const patternParts = [];
        this.defaultFields[name].forEach((field) => {
          expressions.forEach((expression) => {
            const expressionValue = this.exactSearch ? `"${expression}"` : `regex("${expression}", "i")`;
            patternParts.push(`${field} == ${expressionValue}`);
          });
        });
        // Only push if we are in exact search mode and there is a search value
        // if there is no search value we will not add the "search" term
        if (this.exactSearch && search) {
          patternParts.push(`search("${search}")`);
        }
        const filter = patternParts.length ? patternParts.join(' or ') : '';
        this.updateDataView({
          module: name,
          view: {
            query: {
              filter,
              search,
            },
          },
        });
      });
      this.updateEntitiesPerTable();
    },
  },
};
</script>

<style lang="scss">
    .explorer-results {
        height: calc(100% - 48px);

        .x-entity-table {
            height: 50%;

            .x-data-table {
                height: 100%;
            }
        }
    }
</style>
