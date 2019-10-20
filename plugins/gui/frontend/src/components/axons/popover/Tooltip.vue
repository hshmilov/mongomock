<template>
  <div
    class="x-tooltip"
    :class="{ top: position.top, left: position.left }"
    @click.stop=""
  >
    <transition name="bounce">
      <div>
        <div class="tooltip-header">
          <slot name="header" />
        </div>
        <div class="tooltip-body">
          <slot name="body">
            no body: add a body
          </slot>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
    export default {
      name: 'XTooltip',
      data () {
          return {
            position: {
              top: false,
              left: false
            }
          }
      },
      mounted () {
        let boundingBox = this.$el.getBoundingClientRect()
        this.position = {
          top: this.position.top || Boolean(boundingBox.bottom > window.innerHeight - 80),
          left: this.position.left || Boolean(boundingBox.right > window.innerWidth - 24)
        }
      }
    }
</script>

<style lang="scss">
    .x-tooltip {
        position: absolute;
        cursor: default;
        background-color: $theme-white;
        border: 1px solid $grey-2;
        border-radius: 4px;
        padding: 8px;
        z-index: 1000;
        max-width: 600px;
        line-height: 30px;
        font-size: 14px;
        color: $theme-black;
        font-weight: 200;
        &.top {
            bottom: 100%;
        }
        &.left {
            right: 0;
        }
        .tooltip-header {
            color: $grey-3;
            .separator {
                border-bottom: 1px dashed $grey-3;
                display: flex;
            }
            .adapter-icon {
                margin-right: 40px;
            }
        }
        .tooltip-body {
            overflow: auto;
            max-height: 240px;
            @include  x-scrollbar;
            .x-table {
              width: min-content;
              height: auto;
              overflow: visible;
            }
        }
     }

   .bounce-enter-active {
        animation: bounce-in .1s;
    }
    .bounce-leave-active {
        animation: bounce-in .1s reverse;
    }
    @keyframes bounce-in {
        0% {
            transform: scale(0.95);
        }
        50% {
            transform: scale(1.05);
        }
        100% {
            transform: scale(1);
        }
    }
</style>