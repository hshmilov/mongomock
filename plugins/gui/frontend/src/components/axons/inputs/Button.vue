<template>
  <AButton
    :class="{'x-button': true, active}"
    v-bind="$props"
    v-on="$listeners"
  >
    <slot />
  </AButton>
</template>

<script>
import { Button as AButton } from 'ant-design-vue';

export default {
  name: 'XButton',
  components: { AButton },
  props: {
    ...AButton.props,
    active: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style lang="scss">
  .ant-btn-primary {
    width: 120px;
  }
  .ant-btn:not(.ant-btn-circle):not(.ant-btn-inverse-emphasize) {
    border: 0;
  }
  .ant-btn-emphasize {
      background-color: $theme-orange;
      border-color: $theme-orange;
      color: $theme-white;
      &:hover, &:focus {
        color: $theme-white;
        background-color: lighten($theme-orange, 5%);
        border-color: lighten($theme-orange, 5%);
      }
      &:active {
        color: $theme-white;
        background-color: darken($theme-orange, 5%);
        border-color: darken($theme-orange, 5%);
      }
  }
  .ant-btn-inverse {
      background-color: $theme-white;
      color: $theme-blue;
      border: 1px solid $theme-blue;
      &:hover {
        color: lighten($theme-blue, 5%);
        border-color: lighten($theme-blue, 5%);
      }
  }
  .ant-btn-inverse-emphasize {
      background-color: $theme-white;
      color: $theme-orange;
      border: 1px solid $theme-orange;
      &:hover, &:focus {
        color: lighten($theme-orange, 5%);
        border-color: lighten($theme-orange, 5%);
      }
      &:active {
        color: darken($theme-orange, 5%);
        border-color: darken($theme-orange, 5%);
      }
  }
  .ant-btn-link {
      .svg-fill { fill: $theme-blue; }
  }
  .ant-btn-light {
      background-color: $grey-2;
      border-color: $grey-2;
      color: $theme-black;
      width: 30px;
      height: 30px;
      line-height: 24px;
      padding: 4px 0;
      &.active, &.active:hover, &.active:focus {
          background-color: $theme-black;
          color: $grey-2;
      }
      &:hover, &:focus {
        color: lighten($theme-black, 5%);
        background-color: lighten($grey-2, 5%);
        border-color: lighten($grey-2, 5%);
      }
      &:active {
        color: darken($theme-black, 5%);
        background-color: darken($grey-2, 5%);
        border-color: darken($grey-2, 5%);
      }
  }
  .ant-btn-right {
      padding: 3px 12px;
      border-top-left-radius: 0;
      border-bottom-left-radius: 0;
      background-color: $theme-orange;
      border-color: $theme-orange;
      &:hover, &:focus {
        background-color: lighten($theme-orange, 5%);
        border-color: lighten($theme-orange, 5%);
      }
      &:active {
        background-color: darken($theme-orange, 5%);
        border-color: darken($theme-orange, 5%);
      }
  }
</style>
