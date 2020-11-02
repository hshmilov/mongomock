<template>
  <ADrawer
    :destroy-on-close="true"
    :visible="visible"
    :wrap-class-name="wrapClass"
    :wrap-style="wrapStyle"
    :closable="false"
    :width="width"
    :get-container="sidePanelContainer"
    :mask="mask"
    @close="onClose"
  >
    <template #title>
      <span
        class="title"
        :title="title"
      >{{ title }}</span>
      <div class="actions">
        <slot name="panelHeader" />
        <span
          v-if="closeIconVisible"
          class="action-close"
          title="Close"
          @click="onClose"
        >
          <XIcon
            family="action"
            type="close"
          />
        </span>
      </div>
    </template>

    <section class="ant-drawer-body__content">
      <slot name="panelContent" />
    </section>

    <footer
      v-if="$slots.panelFooter"
      class="ant-drawer-body__footer"
    >
      <slot name="panelFooter" />
    </footer>
  </ADrawer>
</template>

<script>
import { Drawer } from 'ant-design-vue';

export default {
  name: 'XSidePanel',
  components: {
    ADrawer: Drawer,
  },
  props: {
    panelContainer: {
      type: Function,
      default: null,
    },
    panelClass: {
      type: String,
      default: '',
    },
    visible: {
      type: Boolean,
      default: false,
    },
    width: {
      type: String,
      default: '800',
    },
    title: {
      type: String,
      default: '',
    },
    mask: {
      type: Boolean,
      default: true,
    },
    closeIconVisible: {
      type: Boolean,
      default: true,
    },
  },
  computed: {
    sidePanelContainer() {
      return this.panelContainer || false;
    },
    wrapClass() {
      return ['x-side-panel', this.panelClass].join(' ');
    },
    wrapStyle() {
      return { position: 'absolute', right: '0px' };
    },
  },
  methods: {
    onClose() {
      this.$emit('close');
    },
  },
};
</script>

<style lang="scss">

  .x-side-panel {

    .ant-drawer-mask {
      position: absolute;
    }

    .ant-drawer-content-wrapper {
      position: absolute;
    }

    .ant-drawer-header {
      width: 100%;
      padding: 16px 28px;
      background-color: $theme-orange;
      align-items: center;
      z-index: 2;
      height: 64px;
      text-overflow: ellipsis;
      white-space: nowrap;
      overflow: hidden;
      border-radius: 0px;

      .ant-drawer-title {
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 32px;

        .title {
          color: #fff;
          max-width: 90%;
          text-overflow: ellipsis;
          white-space: nowrap;
          overflow: hidden;
        }

        .actions {
          display: flex;
          height: 25px;

          .x-icon {
            font-size: 20px;
            color: $theme-white;
          }

          .action-close {
            font-size: 20px;
            line-height: 25px;
            color: $theme-white;
            cursor: pointer;
          }

          ul {
            list-style: none;
            display: flex;

            li {
              padding: 0 4px;
              cursor: pointer;
            }
          }
        }
      }
    }

    .ant-drawer-body {
      height: calc(100% - 64px);
      padding: 24px 0px 24px 24px;
      width: 100%;

      &__content {
        position: relative;
        padding: 5px 28px 110px 5px;
        height: calc(100% - 32px);
        overflow-y: auto;
        @include  y-scrollbar;
      }
      &__footer {
        position: absolute;
        padding: 5px 30px 0 30px;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #fff;
        height: 50px;
      }
    }
  }


</style>
