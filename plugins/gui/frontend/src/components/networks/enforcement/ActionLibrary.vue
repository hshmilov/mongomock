<template>
  <div class="x-action-library">
    <x-search-input v-model="searchValue" />
    <md-list
      class="actions-container"
      :md-expand-single="true"
    >
      <md-list-item
        v-for="category in processedCategories"
        :key="category.name"
        :md-expand="true"
      >
        <x-title :logo="`actions/${category.name}`">{{ category.title }}</x-title>
        <md-list
          slot="md-expand"
        >
          <md-list-item
            v-for="action in category.items"
            :key="action.name"
            @click="onClickAction(action)"
          >
            <x-title
              :logo="`actions/${action.name}`"
              :disabled="!action.implemented"
            >
              <div
                class="action-name"
              >
                <img
                  v-if="!action.implemented"
                  :src="require('Logos/actions/idea.png')"
                  class="md-image"
                  alt="Future Action"
                >
                <img
                  v-else-if="action.locked"
                  :src="require('Logos/actions/lock.png')"
                  class="md-image"
                  alt="Locked Action"
                >
                <div v-else class="md-image"></div>
                <div>{{ action.title }}</div>
              </div>
            </x-title>
          </md-list-item>
        </md-list>
      </md-list-item>
    </md-list>
    <x-action-library-tip
      :action="actionToTip"
      @close="actionToTip = null"
    />
  </div>
</template>

<script>
  import xTitle from '../../axons/layout/Title.vue'
  import xSearchInput from '../../neurons/inputs/SearchInput.vue'
  import xActionLibraryTip from './ActionLibraryTip.vue'
  import actionsMixin from '../../../mixins/actions'
  import { actionsMeta } from '../../../constants/enforcement'

  import {mapState, mapActions} from 'vuex'
  import {LOAD_PLUGIN_CONFIG} from '../../../store/modules/settings'

  export default {
    name: 'XActionLibrary',
    components: {
      xTitle, xSearchInput, xActionLibraryTip
    },
    mixins: [actionsMixin],
    props: {
      categories: {
        type: Array,
        required: true
      }
    },
    data () {
      return {
        searchValue: '',
        actionToTip: null
      }
    },
    computed: {
      ...mapState({
        lockedActions(state) {
          if (!state.settings.configurable.gui || !state.settings.configurable.gui.FeatureFlags) return null
          return state.settings.configurable.gui.FeatureFlags.config.locked_actions
        }
      }),
      processedCategories () {
        return this.categories.map(category => {
          return {
            name: category,
            title: actionsMeta[category].title,
            items: actionsMeta[category].items
                    .map(action => {
                      return {
                        name: action,
                        title: actionsMeta[action].title,
                        implemented: this.actionsDef[action] !== undefined,
                        locked: this.lockedActions && this.lockedActions.includes(action)
                      }
                    })
                    .filter(action => action.title.toLowerCase().includes(this.searchValue.toLowerCase()))
          }
        }).filter(category => category.items.length)
      }
    },
    mounted() {
      if (!this.lockedActions || !this.lockedActions.length) {
        this.loadPluginConfig({
          pluginId: 'gui',
          configName: 'FeatureFlags'
        })
      }
    },
    methods: {
      ...mapActions({
        loadPluginConfig: LOAD_PLUGIN_CONFIG
      }),
      disabled (action) {
        return !this.actionsDef[action]
      },
      onClickAction (action) {
        this.checkEmptySettings(action.name)
        if (this.anyEmptySettings) return
        if (action.locked || !action.implemented) {
          this.actionToTip = action
          return
        }
        this.$emit('select', action.name)
      }
    }
  }
</script>

<style lang="scss">
  .x-action-library {
    .actions-container {
      overflow: auto;
      height: calc(100% - 36px);

      .x-title {
        .md-image {
          height: 36px;
        }

        .action-name {
          display: flex;
          align-items: center;
          .md-image {
            width: 14px;
            margin-right: 8px;
            height: auto;
          }
        }
      }

      .md-list-expand {
        margin-left: 36px;
      }
    }
  }
</style>