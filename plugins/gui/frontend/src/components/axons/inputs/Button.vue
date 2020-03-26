<template>
  <AButton
    class="x-button"
    :type="type"
    :disabled="disabled"
    :class="{inverse, inverseEmphasize, light, right, link, great, emphasize, active}"
    @click="onClick"
  >
    <slot />
  </AButton>
</template>

<script>
export default {
  name: 'XButton',
  props: {
    disabled: {
      type: Boolean,
      default: false,
    },
    inverse: {
      type: Boolean,
      default: false,
    },
    inverseEmphasize: {
      type: Boolean,
      default: false,
    },
    light: {
      type: Boolean,
      default: false,
    },
    right: {
      type: Boolean,
      default: false,
    },
    link: {
      type: Boolean,
      default: false,
    },
    great: {
      type: Boolean,
      default: false,
    },
    emphasize: {
      type: Boolean,
      default: false,
    },
    active: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    type() {
      if (this.link) {
        return 'link';
      }
      return 'primary';
    },
  },
  methods: {
    onClick(e) {
      if (this.disabled) {
        this.$emit('access');
        e.preventDefault();
        return false;
      }
      this.$emit('click', e);
      return true;
    },
  },
};
</script>

<style lang="scss">
    .ant-btn.x-button {
        border: 0;
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.2s ease-in;
        text-align: center;
        width: 120px;
        font: 300 14px Roboto;
        line-height: 20px;
        &.inverse {
            background-color: $theme-white;
            color: $theme-blue;
            border: 1px solid $theme-blue;
        }
        &.inverseEmphasize {
            background-color: $theme-white;
            color: $theme-orange;
            border: 1px solid $theme-orange;
        }
        &.light {
            background-color: $grey-2;
            border-color: $grey-2;
            color: $theme-black;
            width: 30px;
            height: 30px;
            line-height: 24px;
            padding: 4px 0;
            &.active {
                background-color: $theme-black;
                color: $grey-2;
            }
        }
        &.right {
            width: auto;
            padding: 3px 12px;
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
        }
        &.link {
            width: auto;
            .svg-fill { fill: $theme-blue; }
        }
        &.great {
            font-size: 16px;
            line-height: 30px;
        }
        &.emphasize {
            background-color: $theme-orange;
            border-color: $theme-orange;
        }
        .svg-fill { fill: $theme-white; }
        .svg-stroke { stroke: $theme-white; }
    }
</style>
