<template>
  <div class="x-action-library">
    <XSearchInput
      v-model="searchValue"
      :auto-focus="false"
    />
    <MdList
      class="actions-container"
      :md-expand-single="true"
    >
      <MdListItem
        v-for="category in processedCategories"
        :key="category.name"
        :md-expand="true"
      >
        <XTitle :logo="`actions/${category.name}`">{{ category.title }}</XTitle>
        <MdList
          slot="md-expand"
        >
          <MdListItem
            v-for="action in category.items"
            :id="`test_${action.name}`"
            :key="action.name"
            @click="onClickAction(action)"
          >
            <XTitle
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
                <div
                  v-else
                  class="md-image"
                />
                <div>{{ action.title }}</div>
              </div>
            </XTitle>
          </MdListItem>
        </MdList>
      </MdListItem>
    </MdList>
    <XActionLibraryTip
      :action="actionToTip"
      @close="actionToTip = null"
    />
  </div>
</template>

<script>
import { mapState } from 'vuex';
import _get from 'lodash/get';
import XTitle from '../../axons/layout/Title.vue';
import XSearchInput from '../../neurons/inputs/SearchInput.vue';
import XActionLibraryTip from './ActionLibraryTip.vue';
import actionsMixin from '../../../mixins/actions';
import { actionsMeta } from '../../../constants/enforcement';

export default {
  name: 'XActionLibrary',
  components: {
    XTitle, XSearchInput, XActionLibraryTip,
  },
  mixins: [actionsMixin],
  props: {
    categories: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      searchValue: '',
      actionToTip: null,
    };
  },
  computed: {
    ...mapState({
      featureFlags: (state) => _get(state, 'settings.configurable.gui.FeatureFlags.config', null),
    }),
    lockedActions() {
      return this.featureFlags ? this.featureFlags.locked_actions : null;
    },
    processedCategories() {
      return this.categories.map((category) => ({
        name: category,
        title: actionsMeta[category].title,
        items: actionsMeta[category].items
          .map((action) => ({
            name: action,
            title: actionsMeta[action].title,
            implemented: this.actionsDef[action] !== undefined,
            locked: this.lockedActions && this.lockedActions.includes(action),
          }))
          .filter((action) => action.title.toLowerCase().includes(this.searchValue.toLowerCase())),
      })).filter((category) => category.items.length);
    },
  },
  methods: {
    disabled(action) {
      return !this.actionsDef[action];
    },
    onClickAction(action) {
      if (action.locked || !action.implemented) {
        this.actionToTip = action;
        return;
      }
      this.checkEmptySettings(action.name);
      if (this.anyEmptySettings) return;
      this.$emit('select', action.name);
    },
  },
};
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
