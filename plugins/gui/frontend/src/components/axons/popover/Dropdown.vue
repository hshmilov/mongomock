<template>
  <div
    class="x-dropdown"
    :class="{ active: isActive, disabled: readOnly }"
  >
    <div class="dropdown-input">
      <div
        :class="{trigger: true, arrow}"
        data-toggle="dropdown"
        aria-haspopup="true"
        :aria-expanded="isActive"
        @click="toggle"
        @keyup.enter="toggle"
        @keyup.down="open"
        @keyup.up="close"
        @keyup.esc="close"
      >
        <slot name="trigger" />
      </div>
      <div
        v-if="isActive"
        class="x-dropdown-bg"
        :style="overlayPositionStyling"
        @click="close"
      />
    </div>
    <div
      v-if="isActive"
      ref="content"
      :class="`content ${sizeClass}`"
      :style="contentStyle"
    >
      <slot name="content" />
    </div>
  </div>
</template>

<script>
import _clone from 'lodash/clone';

export default {
  name: 'XDropdown',
  props: {
    size: { default: '' },
    align: { default: 'left' },
    alignAgile: { default: true },
    arrow: { default: true },
    readOnly: { default: false },
    overflow: { default: true },
    noBorderRadius: { default: false },
  },
  data() {
    return {
      isActive: false,
      contentStyle: { bottom: 0, right: 0 },
      lastBottomPosition: 0,
      positionSet: false,
    };
  },
  computed: {
    sizeClass() {
      if (this.size) {
        return `w-${this.size}`;
      }
      return '';
    },
    overlayPositionStyling() {
      const closestDrawerAncestor = this.$el.closest('.ant-drawer');
      if (!closestDrawerAncestor) {
        return {};
      }
      let { top } = closestDrawerAncestor.getBoundingClientRect();
      top = `-${top}px`;
      return {
        top,
        right: '-24px',
        left: 'auto',
        height: 'calc(100vh - 24px)',
      };
    },
  },
  updated() {
    if (!this.noBorderRadius || !this.positionSet) return;

    const contentElement = this.$refs.content;
    if (contentElement) {
      const boundingRect = contentElement.getBoundingClientRect();

      // No need to do anything if position didn't change.
      if (this.lastBottomPosition === boundingRect.bottom) return;

      const styles = _clone(this.contentStyle);
      if (boundingRect.bottom + 30 > window.innerHeight) {
        styles.overflow = 'auto';
      } else {
        styles.overflow = 'none';
      }
      this.contentStyle = styles;
      this.lastBottomPosition = boundingRect.bottom;
    }
  },
  methods: {
    toggle() {
      if (!this.readOnly) {
        this.isActive = !this.isActive;
        this.activeChanged();
      }
    },
    open() {
      if (!this.readOnly) {
        this.isActive = true;
        this.activeChanged();
      }
    },
    close() {
      this.isActive = false;
      this.lastBottomPosition = 0;
      this.contentStyle = {};
    },
    activeChanged() {
      if (this.isActive) {
        this.$nextTick(() => {
          this.calculateContentStyle();
          this.$emit('activated');
        });
      }
    },
    calculateContentStyle() {
      const styles = {};
      const boundingRect = this.$el.getBoundingClientRect();
      if (this.align === 'right') {
        const scrollbarWidth = window.innerWidth - document.body.offsetWidth;
        const right = window.innerWidth - boundingRect.left - boundingRect.width - scrollbarWidth;
        styles.right = `${right}px`;
        styles.left = 'auto';
      }

      styles[this.overflow ? 'min-width' : 'max-width'] = `${boundingRect.width}px`;
      const dropdownInputBottom = boundingRect.top + this.$el.offsetHeight;

      if (this.noBorderRadius) {
        styles['border-radius'] = '0px';
      }

      this.positionSet = true;
      if (!this.alignAgile) {
        styles['max-height'] = `calc(100% - ${dropdownInputBottom}px)`;
        if (!this.noBorderRadius) {
          styles.overflow = 'auto';
        }
        this.contentStyle = styles;
        return;
      }

      const contentBottomPosition = dropdownInputBottom + this.$refs.content.offsetHeight;
      let top;
      if (contentBottomPosition > window.innerHeight) {
        top = boundingRect.top - this.$refs.content.offsetHeight;
      } else {
        top = dropdownInputBottom;
      }
      const closestDrawerAncestor = this.$el.closest('.ant-drawer');
      if (closestDrawerAncestor) {
        top -= closestDrawerAncestor.getBoundingClientRect().top;
      }
      styles.top = `${top}px`;
      this.contentStyle = styles;
    },
    clearStyles() {
      this.calculateContentStyle();
    },
  },
};
</script>

<style lang="scss">
    .x-dropdown {

        .dropdown-input {
            position: relative;
        }

        .trigger {
            cursor: pointer;
            &.arrow:after {
                right: 8px;
                @include triangle('down', 0.35rem);
            }
        }

        &.disabled .trigger {
            cursor: default;
        }

        > .content {
            background-color: $theme-white;
            position: fixed;
            z-index: 300;
            padding: 12px;
            border-radius: 4px;
            box-shadow: $popup-shadow;
        }

        .x-dropdown-bg {
            position: fixed;
            z-index: 299;
            background: transparent;
            height: 100vh;
            width: 100vw;
            top: 0;
            left: 0;
            cursor: default;
        }
    }
</style>
