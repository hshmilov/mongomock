<template>
  <VNavigationDrawer
    :class="['x-side-panel', panelClass]"
    :value="value"
    absolute
    :temporary="temporary"
    right
    :width="width"
    @input="stateChanged"
  >
    <header class="x-side-panel__header">
      <span
        class="title"
        :title="title"
      >{{ title }}</span>
      <div class="actions">
        <slot name="panelHeader" />
        <span
          class="action-close"
          title="Close"
        >
          <VIcon
            size="20"
            color="#fff"
            @click="closePanel"
          >{{ closeSvgIconPath }}
          </VIcon>
        </span>
      </div>
    </header>
    <section class="x-side-panel__content">
      <slot name="panelContent" />
    </section>
    <footer
      v-if="$slots.panelFooter"
      class="x-side-panel__footer"
    >
      <slot name="panelFooter" />
    </footer>
  </VNavigationDrawer>
</template>

<script>
import { mdiClose } from '@mdi/js';

export default {
  name: 'XSidePanel',
  props: {
    panelClass: {
      type: String,
      default: '',
    },
    value: {
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
    temporary: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      closeSvgIconPath: mdiClose,
    };
  },
  methods: {
    stateChanged(panelState) {
      this.$emit('input', panelState);
    },
    closePanel() {
      this.$emit('input', false);
    },
  },
};
</script>

<style lang="scss">
.x-side-panel {
    height: 100%;
    z-index: 1002;

    &__header {
        position: fixed;
        top: 0;
        width: 100%;
        display: flex;
        justify-content: space-between;
        padding: 16px 28px;
        background-color: $theme-orange;
        align-items: center;
        z-index: 2;
        height: 64px;
        text-overflow: ellipsis;
        white-space: nowrap;
        overflow: hidden;

        .title {
            color: #fff;
            max-width: 90%;
            text-overflow: ellipsis;
            white-space: nowrap;
            overflow: hidden;
        }

        .actions {
            display: flex;
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

    &__content {
        padding: 28px 28px 110px 28px;
        position: relative;
        top: 64px;
    }


    &__footer {
        position: absolute;
        bottom: 0;
        width: 100%;
        padding: 28px;
        background-color: #fff;
    }
}
</style>
