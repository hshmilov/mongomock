<template>
  <div>
    <div class="x-search-insights">
      <AInputSearch
        v-model="searchValue"
        placeholder="Search by Host Name, User Name, Manufacturer Serial, MAC or IP..."
        :disabled="!canViewAnyEntity"
        enter-button="Search"
        @search="onSearch"
        @keydown.enter.native="onSearch"
      />
    </div>
    <XAccessModal v-model="blockedComponent" />
  </div>
</template>

<script>
import { mapState, mapMutations } from 'vuex';
import { Input } from 'ant-design-vue';
import XAccessModal from '../popover/AccessModal.vue';

import { UPDATE_DATA_VIEW } from '../../../store/mutations';
import { entities } from '../../../constants/entities';

export default {
  name: 'XSearchInsights',
  components: { XAccessModal, AInputSearch: Input.Search },
  data() {
    return {
      blockedComponent: '',
    };
  },
  computed: {
    ...mapState({
      entitiesView(state) {
        return entities.reduce((map, { name }) => ({ ...map, [name]: state[name].view }), {});
      },
    }),
    canViewAnyEntity() {
      return entities.filter((entity) => this.$canViewEntity(entity.name)).length > 0;
    },
    searchValue: {
      get() {
        return this.entitiesView[entities[0].name].query.search || '';
      },
      set(value) {
        this.updateSearchValue(value);
      },
    },
  },
  methods: {
    ...mapMutations({
      updateDataView: UPDATE_DATA_VIEW,
    }),
    updateSearchValue(search) {
      entities.forEach((entity) => {
        this.updateDataView({
          module: entity.name,
          view: {
            query: {
              search,
              filter: this.entitiesView[entity.name].query.filter,
            },
          },
        });
      });
    },
    onSearch() {
      this.$emit('search', this.searchValue);
    },
  },
};
</script>

<style lang="scss">
    .x-search-insights {
        display: flex;
        width: 60vw;
        margin: auto auto 12px;

        .ant-btn {
          background-color: $theme-orange;
          border-color: $theme-orange;
          &:hover {
            background-color: rgba($color: $theme-orange, $alpha: 0.85);
            border-color: rgba($color: $theme-orange, $alpha: 0.85);
          }
        }
    }
</style>
