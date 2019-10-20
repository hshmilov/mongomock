<template>
  <div
    class="x-tabs"
    :class="{ vertical }"
  >
    <ul class="header">
      <li
        v-for="tab in validTabs"
        :id="tab.id"
        :key="tab.id"
        class="header-tab"
        :class="{active: tab.isActive, disabled: tab.disabled}"
        @click="selectTab(tab.id)"
        @dblclick="() => renameTab(tab)"
      >
        <x-title
          v-if="tab.logo"
          :logo="tab.logo"
        >{{ tab.title }}</x-title>
        <div
          v-else
          class="text"
          :title="tab.title"
        >{{ tab.title }}</div>
        <x-button
          v-if="tab.removable"
          link
          @click.stop="() => removeTab(tab)"
        >x</x-button>
      </li>
      <li
        v-if="extendable"
        class="add-tab"
        @click="$emit('add')"
      >+</li>
    </ul>
    <div class="body">
      <slot />
    </div>
    <x-modal
      v-if="tabToRename.id"
      size="md"
      :disabled="disableConfirmRename"
      @confirm="confirmRenameTab"
      @close="cancelRenameTab"
    >
      <div slot="body">
        <label for="rename_tab">Rename:</label>
        <input
          id="rename_tab"
          v-model="tabToRename.name"
          type="text"
          @keydown.enter="confirmRenameTab"
        >
      </div>
    </x-modal>
    <x-modal
      v-if="tabToRemove"
      size="lg"
      :approve-text="removeText"
      @confirm="confirmRemoveTab"
      @close="cancelRemoveTab"
    >
      <div slot="body">
        <slot name="remove_confirm" />
        <div>Do you want to continue?</div>
      </div>
    </x-modal>
  </div>
</template>

<script>
import xTitle from '../layout/Title.vue'
import xButton from '../inputs/Button.vue'
import xModal from '../popover/Modal.vue'

export default {
  name: 'XTabs',
  components: {
    xTitle,
    xButton,
    xModal
  },
  props: {
    vertical: {
      type: Boolean,
      default: false
    },
    extendable: {
      type: Boolean,
      default: false
    },
    removeText: {
      type: String,
      default: 'Remove'
    }
  },
  data() {
    return {
      tabs: [],
      tabToRename: { id: '', name: '' },
      tabToRemove: null
    }
  },
  computed: {
    validTabs() {
      return this.tabs.filter(tab => tab.id !== undefined)
    },
    disableConfirmRename() {
      return Boolean(!this.tabToRename.name)
    }
  },
  created() {
    this.tabs = this.$children
  },
  mounted() {
    if (this.$route.hash) {
      this.selectTab(this.$route.hash.slice(1))
    }
  },
  methods: {
    selectTab(selectedId) {
      let found = false
      this.tabs.forEach(tab => {
        tab.isActive = tab.id === selectedId
        if (tab.isActive) found = true
      })
      if (!found) {
        this.tabs[0].isActive = true
      }
      this.$emit('click', selectedId)
    },
    renameTab(tab) {
      if (!tab.editable) return
      this.tabToRename = {
        id: tab.id,
        name: tab.title
      }
    },
    renameTabById(tabId) {
      this.renameTab(this.validTabs.find(tab => tab.id === tabId))
    },
    confirmRenameTab() {
      if (!this.tabToRename.name) return
      this.$emit('rename', {
        id: this.tabToRename.id,
        name: this.tabToRename.name
      })
      this.cancelRenameTab()
    },
    cancelRenameTab() {
      this.tabToRename = { id: '', name: '' }
    },
    removeTab(tab) {
      this.tabToRemove = tab
    },
    confirmRemoveTab() {
      this.$emit('remove', this.tabToRemove.id)
      if (this.tabToRemove.isActive && this.tabs.length) {
        this.selectTab(this.tabs[0].id)
      }
      this.cancelRemoveTab()
    },
    cancelRemoveTab() {
      this.tabToRemove = null
    }
  }
}
</script>


<style lang="scss" scoped>
.x-tabs {
  width: 100%;
  height: 100%;
  .header {
    list-style: none;
    display: flex;
    overflow-y: hidden;

    .header-tab {
      position: relative;
      padding: 12px 24px 12px 48px;
      background: $grey-2;
      display: flex;
      white-space: nowrap;
      cursor: pointer;

      .text {
        max-width: 240px;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      img {
        margin-right: 4px;
      }

      .x-button {
        display: none;
        padding: 0;
        position: absolute;
        right: 0;
        z-index: 1000;
        cursor: pointer;
      }
      &:hover {
        .x-button {
          display: block;
        }
      }

      &.active {
        background: $theme-white;

        &:after {
          background: $theme-white;
        }
      }

      &:hover {
        text-shadow: $text-shadow;
      }

      &:after {
        content: '';
        position: absolute;
        background: $grey-2;
        height: 52px;
        width: 24px;
        right: -16px;
        z-index: 20;
        top: -1px;
        transform: rotate(-15deg);
        border-top-right-radius: 50%;
      }
    }

    .add-tab {
      padding: 0 36px;
      line-height: 42px;
      color: $theme-orange;
      font-weight: 500;
      font-size: 20px;
      cursor: pointer;
      &:hover {
        text-shadow: $text-shadow;
      }
    }
  }

  > .body {
    height: calc(100% - 48px);
    background-color: $theme-white;
    border-top: 0;
    border-bottom-right-radius: 4px;
    border-bottom-left-radius: 4px;
    padding: 12px;
    overflow: auto;
  }
  &.vertical {
    display: flex;

    > .header {
      display: block;
      border-right: 2px solid $grey-1;
      overflow: auto;
      margin-left: -12px;
      width: 200px;

      .header-tab {
        padding: 24px;
        background: $theme-white;
        white-space: pre-line;

        &:after {
          content: none;
        }

        &.active {
          background-color: $grey-1;
        }

        .title {
          white-space: pre-line;
        }
      }
    }

    .body {
      flex: 1 0 auto;
      height: 100%;
      width: calc(100% - 200px);
    }
  }
  &::v-deep .x-modal {
    #rename_tab {
      margin-left: 12px;
    }
  }
}
</style>
