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
  import featureFlagsMixin from '../../../mixins/feature_flags'
  import { actionsMeta } from '../../../constants/enforcement'


  export default {
    name: 'XActionLibrary',
    components: {
      xTitle, xSearchInput, xActionLibraryTip
    },
    mixins: [actionsMixin, featureFlagsMixin],
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
      lockedActions() {
        return this.featureFlags ? this.featureFlags.locked_actions : null
      },
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
    methods: {
      disabled (action) {
        return !this.actionsDef[action]
      },
      onClickAction (action) {
        if (action.locked || !action.implemented) {
          this.actionToTip = action
          return
        }
        this.checkEmptySettings(action.name)
        if (this.anyEmptySettings) return
        this.$emit('select', action.name)
      }
    }
  }
</script>

<style lang="scss">
  .x-action-library {
    height: 100%;
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