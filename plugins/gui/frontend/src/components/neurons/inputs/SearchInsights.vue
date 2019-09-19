<template>
  <div>
    <div class="x-search-insights">
      <x-search-input
        v-model="searchValue"
        placeholder="Search by Host Name, User Name, Manufacturer Serial, MAC or IP..."
        :disabled="entitiesRestricted"
        @keydown.enter.native="onClick"
        @click.native="notifyAccess"
      />
      <x-button
        right
        :disabled="entitiesRestricted"
        @click="onClick"
        @access="notifyAccess"
      >Search</x-button>
    </div>
    <x-access-modal v-model="blockedComponent" />
  </div>
</template>

<script>
  import xButton from '../../axons/inputs/Button.vue'
  import xSearchInput from './SearchInput.vue'
  import xAccessModal from '../popover/AccessModal.vue'

  import { mapState, mapMutations } from 'vuex'
  import { UPDATE_DATA_VIEW } from '../../../store/mutations'
  import { entities } from '../../../constants/entities'

  export default {
    name: 'XSearchInsights',
    components: { xButton, xSearchInput, xAccessModal },
    computed: {
      ...mapState({
        entitiesView (state) {
          return entities.reduce((map, entity) => {
            map[entity.name] = state[entity.name].view
            return map
          }, {})
        },
        entitiesRestricted (state) {
          let user = state.auth.currentUser.data
          if (!user || !user.permissions) return true
          return user.permissions.Devices === 'Restricted' || user.permissions.Users === 'Restricted'
        }
      }),
      searchValue: {
        get () {
          return this.entitiesView[entities[0].name].query.search || ''
        },
        set (value) {
          this.updateSearchValue(value)
        }
      },
      entitiesFields () {
        return {
          devices: [
            'adapters', 'specific_data.data.hostname', 'specific_data.data.name', 'specific_data.data.device_serial',
            'specific_data.data.network_interfaces.ips', 'specific_data.data.network_interfaces.mac',
            'specific_data.data.last_used_users', 'labels'
          ], users: [
            'adapters', 'specific_data.data.username', 'specific_data.data.mail', 'specific_data.data.first_name',
            'specific_data.data.last_name', 'labels'
          ]
        }
      }
    },
    data () {
      return {
        blockedComponent: ''
      }
    },
    mounted() {
      if (this.$route.query.search) {
        this.searchValue = this.$route.query.search
        this.onClick()
      }
    },
    methods: {
      ...mapMutations({
        updateDataView: UPDATE_DATA_VIEW
      }),
      notifyAccess () {
        if (!this.entitiesRestricted) return
        this.blockedComponent = 'Devices and Users Search'
      },
      updateSearchValue (search) {
        entities.forEach(entity => {
          this.updateDataView({
            module: entity.name, view: {
              query: {
                search, filter: this.entitiesView[entity.name].query.filter
              }, fields: this.entitiesFields[entity.name]
            }
          })
        })
      },
      onClick () {
        let expressions = this.searchValue.split(',')
        entities.forEach(entity => {
          let patternParts = []
          this.entitiesView[entity.name].fields.forEach(field => {
            expressions.forEach(expression =>
              patternParts.push(`${field} == regex("${expression.trim()}", "i")`))
          })
          this.updateDataView({
            module: entity.name, view: {
              query: {
                filter: patternParts.join(' or '),
                search: this.searchValue
              }
            }
          })
        })
        this.$emit('click')
      }
    }
  }
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