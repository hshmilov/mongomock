<template>
  <div class="x-action-library">
    <XSearchInput
      v-model="searchValue"
      :disabled="isLoading"
      :auto-focus="false"
    />
    <div class="actions-container">
      <ACollapse
        expand-icon-position="right"
        :bordered="false"
        :active-key="searchValue ? processedCategoriesNames : ''"
      >
        <template #expandIcon="props">
          <AIcon
            :type="props.isActive ? 'up' : 'down'"
          />
        </template>
        <APanel
          v-for="category in processedCategories"
          :key="category.name"
          force-render
          :disabled="isLoading"
        >
          <template #header>
            <XTitle
              v-show="!isLoading"
              :logo="`actions/${category.name}`"
            >{{ category.title }}</XTitle>
            <ASkeleton
              :loading="isLoading"
              active
              :avatar="{ shape: 'circle', size: 'large' }"
              :title="{ width: '35%'}"
              :paragraph="false"
            />
          </template>
          <AList>
            <AItem
              v-for="action in category.items"
              :data-testid="`test_${action.name}`"
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
            </AItem>
          </AList>
        </APanel>
      </ACollapse>
    </div>
    <XActionLibraryTip
      v-if="actionToTip"
      :action="actionToTip"
      @close="actionToTip = null"
    />
  </div>
</template>

<script>
import { mapState } from 'vuex';
import _get from 'lodash/get';
import {
  List as AList,
  Collapse as ACollapse,
  Icon as AIcon,
  Skeleton as ASkeleton,
} from 'ant-design-vue';
import XTitle from '../../axons/layout/Title.vue';
import XSearchInput from '../../neurons/inputs/SearchInput.vue';
import XActionLibraryTip from './ActionLibraryTip.vue';
import actionsMixin from '../../../mixins/actions';
import { actionsMeta } from '../../../constants/enforcement';

export default {
  name: 'XActionLibrary',
  components: {
    XTitle,
    XSearchInput,
    XActionLibraryTip,
    AList,
    ACollapse,
    APanel: ACollapse.Panel,
    AIcon,
    AItem: AList.Item,
    ASkeleton,
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
      isLoading: true,
      imageLoadedCount: 0,
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
          .filter((action) => action.title.toLowerCase().includes(this.searchValue.toLowerCase()) && ((action.title != 'Refetch Asset Entity') || (this.featureFlags && this.featureFlags.refetch_action))),
      })).filter((category) => category.items.length);
    },
    processedCategoriesNames() {
      return this.processedCategories.map((c) => c.name);
    },
  },
  created() {
    this.preloadCategoriesLogos();
  },
  methods: {
    preloadCategoriesLogos() {
      this.categories.forEach(async (category) => {
        const img = new Image();
        import(`Logos/actions/${category}.png`).then((res) => {
          img.src = res.default;
          img.onload = this.imageLoaded;
        }).catch(this.imageLoaded); // we want to show the list even if some images will fail
      });
    },
    imageLoaded() {
      this.imageLoadedCount += 1;

      if (this.imageLoadedCount === this.categories.length) this.isLoading = false;
    },
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
    clearSearchValue() {
      this.searchValue = '';
    },
  },
};
</script>

<style lang="scss">
  .x-action-library {
    height: 100%;
    .actions-container {
      @include  y-scrollbar;
      overflow: auto;
      height: 100%;
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

      .ant-collapse {
        background-color: #fff;
      }

      .ant-list-item {
        padding: 7px 40px;
        cursor: pointer;
      }

      .ant-collapse-item,
      .ant-list-item {
        border: none;
        font-size: 16px;
        font-weight: 400;
        color: rgba(0, 0, 0, 0.87);

        .ant-collapse-header {
          padding: 7px 15px;
        }
      }

      .ant-collapse-content-box {
        padding: 5px;
      }
    }
  }
</style>
