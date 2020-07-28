<template>
  <div class="x-query-state">
    <XRoleGateway
      :permission-category="permissionCategory"
      :permission-section="$permissionConsts.categories.SavedQueries"
    >
      <template slot-scope="{ canUpdate }">
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
            v-else-if="selectedView && userCanUpdateSavedQuery"
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
          :disabled="disabled"
          @click="openSaveView"
        >Save As</XButton>
        <ADropDown
          v-else
          :trigger="['click']"
          class="save-as-dropdown"
        >
          <div>
            <XButton
              type="link"
              :disabled="disabled"
              @click.stop="openSaveView"
            >Save As</XButton>
            <XIcon
              type="caret-down"
              class="arrowIcon"
            />
          </div>
          <AMenu slot="overlay">
            <AMenuItem
              key="0"
              id="saveChanges"
              :disabled="disabled || selectedView.predefined || !canUpdate"
              @click="onSaveClicked"
            >Save
            </AMenuItem>
            <AMenuItem
              key="1"
              @click="reloadSelectedView"
              id="discardChanges"
            >Cancel
            </AMenuItem>
          </AMenu>
        </ADropDown>
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
import { Menu, Dropdown } from 'ant-design-vue';
import XIcon from '@axons/icons/Icon';
import XHistoricalDate from '@neurons/inputs/HistoricalDate.vue';
import XSaveModal from '../../saved-queries/SavedQueryModal.vue';

import { UPDATE_DATA_VIEW } from '../../../../store/mutations';
import { SAVE_DATA_VIEW } from '../../../../store/actions';


export default {
  name: 'XQueryState',
  components: {
    XButton,
    XHistoricalDate,
    XSaveModal,
    ADropDown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
    XIcon,
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
        // Notice that if there is no selected view, the "short circuit evaluation" trick simply
        // returns an empty value for the uuid as a fallback mechanism.
        const { uuid } = state[this.module].selectedView || {};
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
                && !this.hasColFilters()
                && !this.hasColExcludedAdapters();
    },
    isEdited() {
      if (!this.selectedView || !this.selectedView.view) {
        return false;
      }
      const { view } = this.selectedView;
      const {
        query, fields, sort, colFilters, colExcludedAdapters,
      } = this.view;
      const filterDiff = query.filter !== view.query.filter;
      const fieldsDiff = !_isEqual(fields, view.fields);
      const sortDiff = sort.field !== view.sort.field || sort.desc !== view.sort.desc;
      const colFiltersDiff = colFilters
        && view.colFilters && !_isEqual(colFilters, view.colFilters);
      const colExcludedAdaptersDiff = colExcludedAdapters
        && view.colExcludedAdapters && !_isEqual(colExcludedAdapters, view.colExcludedAdapters);
      return view
      && (filterDiff || fieldsDiff || sortDiff || colFiltersDiff || colExcludedAdaptersDiff);
    },
    status() {
      if (this.enforcement) return '';
      const edited = this.isEdited ? '[Edited]' : '';
      return !this.selectedView ? '[Unsaved]' : edited;
    },
    userCanUpdateSavedQuery() {
      return this.$can(this.permissionCategory,
        this.$permissionConsts.actions.Update, this.$permissionConsts.categories.SavedQueries)
        || this.selectedView.private;
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
      this.$emit('reset-search');
    }, 400, { leading: true, trailing: false }),
    navigateFilteredTask() {
      this.$router.push({ path: `/tasks/${this.enforcement.id}` });
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
        private: this.selectedView.private,
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
    hasColFilters() {
      return Object.values(this.view.colFilters).some((cf) => cf.some((f) => !f.include || f.term.trim() !== ''));
    },
    hasColExcludedAdapters() {
      return Object.values(this.view.colExcludedAdapters).length;
    },
    onSaveClicked() {
      this.$safeguard.show({
        text: 'The selected Saved Query will be overridden. Do you wish to continue?',
        confirmText: 'Yes, Save',
        onConfirm: () => {
          this.saveSelectedView();
        },
      });
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
      margin-bottom: 4px;

      .header {
        display: flex;
        line-height: 28px;
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
          display: flex;
          align-items: center;
        }
      }

      > .x-button,
      .dropdown-input .x-button {
        padding: 4px;
        margin-right: 16px;
      }
      .save-as-dropdown {
        font-size: 16px;

        .arrowIcon{
        font-size: .7em;
        padding: 5px 5px 0px 5px;
        transform: translateX(-1.4em);
        cursor: pointer;
        }
      }
    }
  }

</style>
