<template>
  <div class="x-query">
    <x-query-state
      :module="module"
      :disabled="disableSaveQuery"
      @tour="tour"
    />
    <div class="filter">
      <x-query-search-input
        v-model="queryFilter"
        :module="module"
        :valid="filterValid"
        :query-search="query.search"
        @activated="tour('querySelect')"
        @validate="filterValid = true"
      />
      <x-button
        link
        @click="navigateSavedQueries"
      >Saved Queries</x-button>
      <x-query-wizard
        v-model="queryFilter"
        :module="module"
        @activated="tour('queryField')"
        @error="filterValid = false"
      />
    </div>
  </div>
</template>

<script>
  import xQueryState from './State.vue'
  import xQuerySearchInput from './SearchInput.vue'
  import xQueryWizard from './Wizard.vue'
  import xButton from '../../../axons/inputs/Button.vue'

  import { mapState, mapGetters, mapMutations, mapActions } from 'vuex'
  import { GET_DATA_FIELDS_BY_PLUGIN } from '../../../../store/getters'
  import { UPDATE_DATA_VIEW } from '../../../../store/mutations'
  import { SAVE_DATA_VIEW } from '../../../../store/actions'
  import { CHANGE_TOUR_STATE } from '../../../../store/modules/onboarding'

  export default {
    name: 'XQuery',
    components: {
      xQueryState, xQuerySearchInput, xQueryWizard, xButton
    },
    props: {
      module: {
        type: String,
        required: true
      },
      readOnly: {
        type: Boolean,
        default: false
      }
    },
    data () {
      return {
        filterValid: true
      }
    },
    computed: {
      ...mapState({
        view (state) {
          return state[this.module].view
        }
      }),
      ...mapGetters({
        getDataFieldsByPlugin: GET_DATA_FIELDS_BY_PLUGIN
      }),
      query () {
        return this.view.query
      },
      enforcementFilter () {
        if (!this.view.enforcement) return ''
        return this.view.enforcement.filter
      },
      queryFilter: {
        get () {
          return this.query.filter
        },
        set (filter) {
          if (this.enforcementFilter) {
            filter = `${this.enforcementFilter} ${filter}`
          }
          this.updateView({
            module: this.module, view: {
              query: {
                filter: filter,
                expressions: this.query.expressions },
              page: 0
            }
          })
          this.filterValid = true
        }
      },
      disableSaveQuery () {
        /* Determine whether query cannot be saved right now or it can */
        return this.readOnly || this.queryFilter === '' || !this.filterValid
      }
    },
    methods: {
      ...mapMutations({
        updateView: UPDATE_DATA_VIEW, changeState: CHANGE_TOUR_STATE
      }),
      ...mapActions({
        saveView: SAVE_DATA_VIEW
      }),
      tour (stateName) {
        this.changeState({ name: stateName })
      },
      navigateSavedQueries () {
        this.$router.push({ path: `/${this.module}/query/saved` })
      }
    }
  }
</script>

<style lang="scss">
    .x-query {

        > .filter {
          display: flex;
        }
    }
</style>