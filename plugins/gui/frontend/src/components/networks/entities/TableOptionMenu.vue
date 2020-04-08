<template>
  <div class="x-option-menu">
    <VMenu
      bottom
      left
      origin="top"
      class="x-option-menu"
      content-class="x-option-menu__content"
    >
      <template v-slot:activator="{ on }">
        <VBtn
          icon
          v-on="on"
        >
          <VIcon color="black">
            {{ dotsIcon }}
          </VIcon>
        </VBtn>
      </template>
      <VList
        ref="list"
        dense
      >
        <VListItem @click="openColumnEditor">
          <VListItemTitle>Edit Columns</VListItemTitle>
        </VListItem>
        <VListItem @click="resetColumnsToUserDefault">
          <VListItemTitle>{{ resetToUserDefaultMenuTitle }}</VListItemTitle>
        </VListItem>
        <VListItem @click="resetColumnsToSystemDefault">
          <VListItemTitle>{{ resetToSystemDefaultMenuTitle }}</VListItemTitle>
        </VListItem>
        <VListItem
          :disabled="disableExportCsv || exportInProgress"
          @click.stop.prevent="exportTableToCSV"
        >
          <VListItemTitle v-if="exportInProgress">
            <VProgressCircular
              indeterminate
              color="primary"
              :width="2"
              :size="16"
            />Exporting...</VListItemTitle>
          <VListItemTitle v-else>Export CSV</VListItemTitle>
        </VListItem>
      </VList>
    </VMenu>
    <XFieldConfig
      v-if="showColumnEditor"
      :module="module"
      :user-fields-groups.sync="userFieldsGroupsSync"
      @done="done"
      @close="closeColumnEditor"
      @reset-user-fields="resetColumnsToUserDefault"
    />
  </div>
</template>

<script>
import { mdiDotsHorizontal } from '@mdi/js';

import {
  mapMutations, mapActions, mapState, mapGetters,
} from 'vuex';
import _get from 'lodash/get';
import _snakeCase from 'lodash/snakeCase';
import { SHOW_TOASTER_MESSAGE, UPDATE_DATA_VIEW } from '@store/mutations';
import { FETCH_DATA_CONTENT_CSV } from '@store/actions';
import { defaultFields } from '@constants/entities';
import { FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES } from '@store/getters';
import XFieldConfig from './FieldConfig.vue';

export default {
  name: 'XOptionMenu',
  components: {
    XFieldConfig,
  },
  props: {
    module: {
      type: String,
      required: true,
    },
    userFieldsGroups: {
      type: Object,
      default: () => ({ default: defaultFields[this.module] }),
    },
    disableExportCsv: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      exportInProgress: false,
      showColumnEditor: false,
    };
  },
  computed: {
    ...mapState({
      querySearchTemplate(state) {
        return _get(state[this.module].view, 'query.meta.searchTemplate', false);
      },
      templateViews(state) {
        return state[this.module].views.template.content.data || [];
      },
    }),
    ...mapGetters({
      fillUserFieldGroups: FILL_USER_FIELDS_GROUPS_FROM_TEMPLATES,
    }),
    dotsIcon() {
      return mdiDotsHorizontal;
    },
    userFieldsGroupsSync: {
      get() {
        return this.userFieldsGroups;
      },
      set(value) {
        this.$emit('update:user-fields-groups', value);
      },
    },
    resetToUserDefaultMenuTitle() {
      return this.querySearchTemplate ? 'Reset Columns to User Search Default' : 'Reset Columns to User Default';
    },
    resetToSystemDefaultMenuTitle() {
      return this.querySearchTemplate ? 'Reset Columns to System Search Default' : 'Reset Columns to System Default';
    },
  },
  methods: {
    ...mapMutations({
      updateView: UPDATE_DATA_VIEW,
      showToasterMessage: SHOW_TOASTER_MESSAGE,
    }),
    ...mapActions({
      fetchContentCSV: FETCH_DATA_CONTENT_CSV,
    }),
    openColumnEditor() {
      this.showColumnEditor = true;
    },
    closeColumnEditor() {
      this.showColumnEditor = false;
    },
    resetColumnsToUserDefault() {
      let fieldsForReset = this.userFieldsGroups.default;
      if (this.querySearchTemplate) {
        const allFieldsGroup = this.fillUserFieldGroups(this.module, this.userFieldsGroups);
        fieldsForReset = allFieldsGroup[_snakeCase(this.querySearchTemplate.name)];
      }
      this.updateTableColumns(fieldsForReset);
    },
    resetColumnsToSystemDefault() {
      let fieldsForReset = defaultFields[this.module];
      if (this.querySearchTemplate) {
        const template = this.templateViews
          .find((item) => item.name === this.querySearchTemplate.name);
        fieldsForReset = _get(template, 'view.fields', []);
      }
      this.updateTableColumns(fieldsForReset);
    },
    updateTableColumns(fields) {
      this.updateView({
        module: this.module,
        view: {
          fields,
        },
      });
      this.done();
    },
    exportTableToCSV() {
      this.exportInProgress = true;
      this.fetchContentCSV({
        module: this.module,
      }).then(() => {
        this.exportInProgress = false;
        this.$refs.list.$el.click();
      });
    },
    done() {
      this.$emit('done');
    },
  },
};
</script>

<style lang="scss">
.x-option-menu {
  .v-btn {
    width: 24px;
    height: 24px;

    &:hover .v-icon {
      fill: $theme-orange;
    }
  }

  &__content {
    .v-list--dense .v-list-item__title {
      font-weight: 300;

      .v-progress-circular {
        margin-right: 4px;
      }
    }
  }
}
</style>
