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
      >
        <XTitle
          v-if="tab.logo"
          :logo="tab.logo"
        >{{ tab.title }}</XTitle>
        <div
          v-else
          class="text"
          :title="tab.title"
        >{{ tab.title }}</div>
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
  </div>
</template>

<script>
import XTitle from '../layout/Title.vue';

export default {
  name: 'XTabs',
  components: {
    XTitle,
  },
  props: {
    vertical: {
      type: Boolean,
      default: false,
    },
    extendable: {
      type: Boolean,
      default: false,
    },
    activeTabUrl: {
      type: Boolean,
      default: false,
    },
    pageBaseUrl: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      tabs: [],
    };
  },
  computed: {
    validTabs() {
      return this.tabs.filter((tab) => tab.id !== undefined);
    },
  },
  created() {
    this.tabs = this.$children;
  },
  mounted() {
    if (this.$route.hash) {
      this.selectTab(this.$route.hash.slice(1));
    } else if (this.activeTabUrl) {
      const activeTab = this.tabs.findIndex((tab) => tab.isActive);
      if (activeTab > 0) {
        this.$router.replace(`${this.pageBaseUrl}/#${this.tabs[activeTab].id}`);
      }
    }
  },
  methods: {
    selectTab(selectedId) {
      let found = false;
      this.tabs.forEach((tab) => {
        tab.isActive = tab.id === selectedId;
        if (tab.isActive) found = true;
      });
      if (!found) {
        this.tabs[0].isActive = true;
      }
      if (this.activeTabUrl) {
        if (this.tabs[0].isActive) {
          this.$router.replace(`${this.pageBaseUrl}/`);
        } else {
          this.$router.replace(`${this.pageBaseUrl}/#${selectedId}`);
        }
      }
      this.$emit('click', selectedId);
    },
  },
};
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

        .x-title {
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
}
</style>
