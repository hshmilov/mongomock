<template>
  <div :class="`x-banner indicator-bg-${severity}`">
    <div class="content"><slot /></div>
  </div>
</template>

<script>
  export default {
    name: 'XBanner',
    props: {
      severity: {
        type: String,
        default: 'info'
      }
    }
  }
</script>

<style lang="scss">
    .x-banner {
        position: absolute;
        top: 0;
        left: 30vw;
        height: 46px;
        width: 40vw;
        z-index: 2000;
        padding: 0 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        color: $theme-white;
        border-bottom-right-radius: 24px;
        border-bottom-left-radius: 24px;

        &.indicator-bg-error {
            &:before, &:after {
                background-color: $indicator-error;
            }
        }
        &.indicator-bg-warning {
            &:before, &:after {
                background-color: $indicator-warning;
            }
        }
        &.indicator-bg-info {
            &:before, &:after {
                background-color: $indicator-info;
            }
        }

        &:before {
            content: '';
            position: absolute;
            height: 52px;
            width: 16px;
            right: -8px;
            top: -14px;
            transform: rotate(30deg);
            border-bottom-right-radius: 12px;

        }
        &:after {
            content: '';
            position: absolute;
            height: 52px;
            width: 16px;
            left: -8px;
            top: -14px;
            transform: rotate(-30deg);
            border-bottom-left-radius: 12px;
        }

        .content {
          white-space: nowrap;
          text-overflow: ellipsis;
          overflow: hidden;
        }
    }
</style>