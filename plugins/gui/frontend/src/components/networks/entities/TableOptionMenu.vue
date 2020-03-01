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
          <VListItemTitle>Reset Columns to User Default</VListItemTitle>
        </VListItem>
        <VListItem @click="resetColumnsToSystemDefault">
          <VListItemTitle>Reset Columns to System Default</VListItemTitle>
        </VListItem>
        <VListItem
          :disabled="exportInProgress"
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
      :default-fields.sync="defaultFieldsSync"
      @done="done"
      @close="closeColumnEditor"
    />
  </div>
</template>

<script>
import { mdiDotsHorizontal } from '@mdi/js';

import { mapMutations, mapActions } from 'vuex';
import { SHOW_TOASTER_MESSAGE, UPDATE_DATA_VIEW } from '../../../store/mutations';
import { FETCH_DATA_CONTENT_CSV } from '../../../store/actions';

import XFieldConfig from './FieldConfig.vue';
import { defaultFields } from '../../../constants/entities';

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
    defaultFields: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      exportInProgress: false,
      showColumnEditor: false,
    };
  },
  computed: {
    dotsIcon() {
      return mdiDotsHorizontal;
    },
    defaultFieldsSync: {
      get() {
        return this.defaultFields;
      },
      set(value) {
        this.$emit('update:default-fields', value);
      },
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
      this.updateTableColumns(this.defaultFields);
    },
    resetColumnsToSystemDefault() {
      this.updateTableColumns(defaultFields[this.module]);
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
