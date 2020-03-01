<template>
  <div>
    <div class="x-search-insights">
      <XSearchInput
        v-model="searchValue"
        placeholder="Search by Host Name, User Name, Manufacturer Serial, MAC or IP..."
        :disabled="entitiesRestricted"
        @keydown.enter.native="onClick"
        @click.native="notifyAccess"
      />
      <XButton
        right
        :disabled="entitiesRestricted"
        @click="onClick"
        @access="notifyAccess"
      >Search</XButton>
    </div>
    <XAccessModal v-model="blockedComponent" />
  </div>
</template>

<script>
import { mapState, mapMutations, mapGetters } from 'vuex';
import XButton from '../../axons/inputs/Button.vue';
import XSearchInput from './SearchInput.vue';
import XAccessModal from '../popover/AccessModal.vue';

import { UPDATE_DATA_VIEW } from '../../../store/mutations';
import { entities } from '../../../constants/entities';
import { EXACT_SEARCH } from '../../../store/getters';

export default {
  name: 'XSearchInsights',
  components: { XButton, XSearchInput, XAccessModal },
  computed: {
    ...mapState({
      entitiesView(state) {
        return entities.reduce((map, { name }) => ({ ...map, [name]: state[name].view }), {});
      },
      entitiesRestricted(state) {
        const user = state.auth.currentUser.data;
        if (!user || !user.permissions) return true;
        return user.permissions.Devices === 'Restricted' || user.permissions.Users === 'Restricted';
      },
    }),
    ...mapGetters({
      exactSearch: EXACT_SEARCH,
    }),
    searchValue: {
      get() {
        return this.entitiesView[entities[0].name].query.search || '';
      },
      set(value) {
        this.updateSearchValue(value);
      },
    },
    entitiesFields() {
      return {
        devices: [
          'adapters', 'specific_data.data.hostname', 'specific_data.data.name', 'specific_data.data.device_serial',
          'specific_data.data.network_interfaces.ips', 'specific_data.data.network_interfaces.mac',
          'specific_data.data.last_used_users', 'labels',
        ],
        users: [
          'adapters', 'specific_data.data.username', 'specific_data.data.mail', 'specific_data.data.first_name',
          'specific_data.data.last_name', 'labels',
        ],
      };
    },
  },
  data() {
    return {
      blockedComponent: '',
    };
  },
  mounted() {
    if (this.$route.query.search) {
      this.searchValue = this.$route.query.search;
      this.onClick();
    }
  },
  methods: {
    ...mapMutations({
      updateDataView: UPDATE_DATA_VIEW,
    }),
    notifyAccess() {
      if (!this.entitiesRestricted) return;
      this.blockedComponent = 'Devices and Users Search';
    },
    updateSearchValue(search) {
      entities.forEach((entity) => {
        this.updateDataView({
          module: entity.name,
          view: {
            query: {
              search, filter: this.entitiesView[entity.name].query.filter,
            },
            fields: this.entitiesFields[entity.name],
          },
        });
      });
    },
    onClick() {
      const expressions = this.searchValue.split(',');
      entities.forEach(({ name }) => {
        const patternParts = [];
        this.entitiesView[name].fields.forEach((field) => {
          expressions.forEach((expression) => {
            // In case there no search value, use default with regex otherwise no data will return
            const expressionString = `${expression.trim()}`;
            const expressionValue = (this.exactSearch && this.searchValue) ? `"${expressionString}"` : `regex("${expressionString}", "i")`;
            patternParts.push(`${field} == ${expressionValue}`);
          });
        });
        // Only push if we are in exact search mode and there is a search value
        // if there is no search value we will not add the "search" term
        if (this.exactSearch && this.searchValue) {
          patternParts.push(`search("${this.searchValue}")`);
        }
        this.updateDataView({
          module: name,
          view: {
            query: {
              filter: patternParts.join(' or '),
              search: this.searchValue,
            },
            fields: this.entitiesFields[name],
          },
        });
      });
      this.$emit('click');
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
            background-color: $theme-orange;

        }
    }
</style>
