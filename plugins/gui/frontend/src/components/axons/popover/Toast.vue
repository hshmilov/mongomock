<template>
  <div
    class="x-toast"
    :style="{ left }"
  >
    <transition
      name="slide-fade"
      tag="div"
    >
      <div class="body">
        <div class="content">{{ message }}</div>
        <div class="actions">
          <slot />
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
  export default {
    name: 'XToast',
    props: { message: { required: true }, timed: { default: true }, timeout: { default: 4000 } },
    data () {
      return {
        left: ''
      }
    },
    watch: {
      message () {
        this.left = ''
        clearTimeout(this.timer)
        this.timer = setTimeout(() => this.$emit('done'), this.timeout)
      }
    },
    mounted () {
      if (this.timed) {
        this.timer = setTimeout(() => this.$emit('done'), this.timeout)
      }
      this.left = this.getLeftPos()
    },
    updated () {
      if (!this.left) {
        this.left = this.getLeftPos()
      }
    },
    methods: {
      getLeftPos () {
        return `calc(50vw - ${this.$el.offsetWidth / 2}px)`
      }
    }
  }
</script>

<style lang="scss">
    .x-toast {
        position: fixed;
        z-index: 10000000000;
        bottom: 0;

        &.slide-fade-enter, &.slide-fade-leave-to {
            transform: translateY(-100%);
            opacity: 0;
        }

        &.slide-fade-enter-active, &.slide-fade-leave-active {
            transition: all 1s ease-in-out;
        }

        .body {
            padding: 0 12px;
            background: $theme-black;
            color: $theme-white;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            box-shadow: 0 1px 1px rgba(0, 0, 0, .2);
            height: 32px;
            display: flex;
            justify-content: space-between;

            .content {
                line-height: 32px;
            }

            .actions {
                color: $theme-orange;
            }
        }
    }
</style>