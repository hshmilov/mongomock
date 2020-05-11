<template>
  <div>
    <div class="x-search-insights">
      <XSearchInput
        v-model="searchValue"
        placeholder="Search by Host Name, User Name, Manufacturer Serial, MAC or IP..."
        :disabled="!canViewAnyEntity"
        @keydown.enter.native="onSearch"
      />
      <XButton
        type="right"
        :disabled="!canViewAnyEntity"
        @click="onSearch"
      >Search</XButton>
    </div>
    <XAccessModal v-model="blockedComponent" />
  </div>
</template>

<script>
import { mapState, mapMutations } from 'vuex';
import XButton from '../../axons/inputs/Button.vue';
import XSearchInput from './SearchInput.vue';
import XAccessModal from '../popover/AccessModal.vue';

import { UPDATE_DATA_VIEW } from '../../../store/mutations';
import { entities } from '../../../constants/entities';

export default {
  name: 'XSearchInsights',
  components: { XButton, XSearchInput, XAccessModal },
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

        .x-search-input {
            flex: 1 0 auto;
            border-radius: 16px 0 0 16px;

            &.focus {
                border-color: $theme-orange;
            }
        }

        .x-button {
            border-radius: 0 16px 16px 0;
            color: $theme-white;
        }
    }
</style>
