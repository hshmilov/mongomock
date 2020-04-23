<template>
  <div class="x-query-state">
    <XRoleGateway
      :permission-category="permissionCategory"
      :permission-section="$permissionConsts.categories.SavedQueries"
    >
      <template slot-scope="{ canAdd, canUpdate }">
        <div class="header">
          <template v-if="enforcement">
            <div class="query-title">
              {{ enforcement.name }}
            </div>
            <div class="subtitle">
              {{ enforcement.outcome }} results of "{{ enforcement.action }}" action
            </div>
          </template>
          <XButton
            v-else-if="selectedView && canUpdate"
            :disabled="selectedView.predefined"
            type="link"
            class="query-title"
            @click="openEditCurrentQueryModal"
          >{{ selectedView.name }}</XButton>
          <div
            v-else-if="selectedView"
            class="query-title"
          >
            {{ selectedView.name }}
          </div>
          <div
            v-else
            class="query-title"
          >
            New Query
          </div>
          <div class="status">
            {{ status }}
          </div>
        </div>
        <XButton
          v-if="enforcement"
          type="link"
          @click="navigateFilteredTask"
        >Go to Task</XButton>
        <XButton
          v-else-if="!selectedView || !isEdited"
          id="query_save"
          type="link"
          :disabled="disabled || !canAdd"
          @click="openSaveView"
        >Save As</XButton>
        <XDropdown v-else>
          <XButton
            slot="trigger"
            type="link"
            :disabled="disabled || selectedView.predefined || !canUpdate"
            @click.stop="saveSelectedView"
          >Save</XButton>
          <div slot="content">
            <XButton
              type="link"
              :disabled="disabled || !canAdd"
              @click="openSaveView"
            >Save As</XButton>
            <XButton
              type="link"
              @click="reloadSelectedView"
            >Discard Changes</XButton>
          </div>
        </XDropdown>
        <XButton
          type="link"
          @click="resetQuery"
        >Reset</XButton>
        <XHistoricalDate
          v-model="historical"
          :allowed-dates="allowedDates"
          :module="module"
        />
        <XSaveModal
          v-model="viewNameModal.isActive"
          :namespace="module"
          :view="viewNameModal.view"
        />
      </template>
    </XRoleGateway>
  </div>
</template>

<script>
import _isEqual from 'lodash/isEqual';
import { mapState, mapMutations, mapActions } from 'vuex';
import _debounce from 'lodash/debounce';
import { defaultViewForReset, getEntityPermissionCategory } from '@constants/entities';
import XButton from '@axons/inputs/Button.vue';
import XDropdown from '@axons/popover/Dropdown.vue';
import XHistoricalDate from '@neurons/inputs/HistoricalDate.vue';
import XSaveModal from '../../saved-queries/SavedQueryModal.vue';

import { UPDATE_DATA_VIEW } from '../../../../store/mutations';
import { SAVE_DATA_VIEW } from '../../../../store/actions';


export default {
  name: 'XQueryState',
  components: {
    XButton, XDropdown, XHistoricalDate, XSaveModal,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    valid: {
      type: Boolean,
      default: true,
    },
    userFieldsGroups: {
      type: Object,
      default: () => ({ default: [] }),
    },
  },
  data() {
    return {
      viewNameModal: {
        isActive: false,
        view: null,
      },
    };
  },
  computed: {
    ...mapState({
      view(state) {
        return state[this.module].view;
      },
      allowedDates(state) {
        return state.constants.allowedDates[this.module];
      },
      selectedView(state) {
        const uuid = state[this.module].selectedView;
        if (!uuid) return null;
        return state[this.module].views.saved.content.data.find((view) => view.uuid === uuid);
      },
    }),
    permissionCategory() {
      return getEntityPermissionCategory(this.module);
    },
    enforcement() {
      return this.view.enforcement;
    },
    disabled() {
      return !this.valid || this.isDefaultView;
    },
    historical: {
      get() {
        if (!this.view.historical) return '';
        return this.view.historical.substring(0, 10);
      },
      set(newDate) {
        this.updateView({
          module: this.module,
          view: {
            historical: newDate ? this.allowedDates[newDate] : null,
          },
        });
        this.$emit('done');
      },
    },
    title() {
      if (this.enforcement) {
        return '';
      }
      if (this.selectedView) {
        return this.selectedView.name;
      }
      return 'New Query';
    },
    isDefaultView() {
      return this.view.query.filter === ''
                && _isEqual(this.view.fields, this.userFieldsGroups.default)
                && this.view.sort.field === ''
                && (!Object.keys(this.view.colFilters).length
                      || !Object.values(this.view.colFilters).find((val) => val));
    },
    isEdited() {
      if (!this.selectedView || !this.selectedView.view) {
        return false;
      }
      const { view } = this.selectedView;
      const {
        query, fields, sort, colFilters,
      } = this.view;
      const filterDiff = query.filter !== view.query.filter;
      const fieldsDiff = !_isEqual(fields, view.fields);
      const sortDiff = sort.field !== view.sort.field || sort.desc !== view.sort.desc;
      const colFiltersDiff = !this.objsValuesMatch(colFilters, view.colFilters);
      return view && (filterDiff || fieldsDiff || sortDiff || colFiltersDiff);
    },
    status() {
      if (this.enforcement) return '';
      const edited = this.isEdited ? '[Edited]' : '';
      return !this.selectedView ? '[Unsaved]' : edited;
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
    }),
    ...mapActions({
      saveView: SAVE_DATA_VIEW,
    }),

    resetQuery: _debounce(function resetQuery() {
      const resetView = defaultViewForReset(this.module, this.userFieldsGroups.default);
      this.updateView(resetView);
      this.$emit('done');
    }, 400, { leading: true, trailing: false }),
    navigateFilteredTask() {
      this.$router.push({ path: `/enforcements/tasks/${this.enforcement.id}` });
    },
    openSaveView() {
      this.viewNameModal.view = null;
      this.viewNameModal.isActive = true;
    },
    openEditCurrentQueryModal() {
      this.viewNameModal.isActive = true;
      this.viewNameModal.view = {
        uuid: this.selectedView.uuid,
        name: this.selectedView.name,
        description: this.selectedView.description,
      };
    },
    saveSelectedView() {
      if (!this.selectedView || !this.selectedView.uuid) return;

      this.saveView({
        module: this.module,
        name: this.selectedView.name,
        uuid: this.selectedView.uuid,
      });
    },
    reloadSelectedView() {
      this.updateView({
        module: this.module,
        view: { ...this.selectedView.view },
      });
      this.$emit('done');
    },
    objContained(superset, subset) {
      return Object.entries(subset).every(([key, value]) => _isEqual(superset[key], value));
    },
    objsValuesMatch(objA = {}, objB = {}) {
      /*
        This is checking that any key in objA has the same value as the key in objB
        (including undefined - if it is undefined in one and non existent in the other, it passes)
         */
      return this.objContained(objA, objB) && this.objContained(objB, objB);
    },
  },
};
</script>

<style lang="scss">
  .x-query-state {
    .role-gateway {
      display: flex;
      width: 100%;
      align-items: center;

      .header {
        display: flex;
        line-height: 28px;
        margin-bottom: 8px;
        margin-right: 16px;

        .query-title {
          font-size: 16px;
          font-weight: 400;
          color: $theme-black;
          margin-right: 8px;

          &.x-button {
            padding: 0;
            margin-bottom: 0;
          }
        }

        .subtitle {
          font-size: 14px;
        }

        .status {
          color: $grey-3;
        }
      }

      > .x-button {
        margin-bottom: 8px;
        padding: 4px;
        margin-right: 16px;
        height: 28px;
      }

      .x-dropdown {
        margin-right: 16px;

        .trigger {
          padding-right: 8px;

          &:after {
            margin-top: -6px;
          }
        }

        .content {
          &.expand {
            min-width: max-content;
          }

          .x-button {
            display: block;
          }
        }
      }
    }
  }
</style>
