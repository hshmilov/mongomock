<template>
  <div
    class="x-search-input"
    :class="{focus: focused}"
    @click="focus"
  >
    <div class="input-icon">
      <svg-icon
        name="action/search"
        :original="true"
        height="18"
      ></svg-icon>
    </div>
    <input
      ref="input"
      v-model="searchValue"
      type="text"
      class="input-value"
      :disabled="disabled"
      :placeholder="placeholder"
      @input="updateSearchValue"
      @focusout="focused = false"
      @click.stop="focused = true"
    >
  </div>
</template>

<script>
  export default {
    name: 'XSearchInput',
    props: {
      value: {
        type: String,
        default: ''
      },
      placeholder: {
        type: String,
        default: 'Search...'
      },
      disabled: {
        type: Boolean, default: false
      }
    },
    data () {
      return {
        searchValue: this.value,
        focused: false
      }
    },
    watch: {
      value (newValue) {
        this.searchValue = newValue
      }
    },
    mounted () {
      this.focus()
    },
    methods: {
      updateSearchValue () {
        this.$emit('input', this.searchValue)
      },
      focus () {
        if (this.disabled) return
        this.focused = true
        this.$refs.input.focus()
      }
    }
  }
</script>

<style lang="scss">
    .x-search-input {
        padding-right: 12px;
        position: relative;
        border: 1px solid $grey-2;
        background: $grey-dient;

        &.focus {
            border-color: $theme-blue;
        }

        .input-value {
            width: 100%;
            border: none;
            background: transparent;
            padding: 4px 4px 4px 42px;
        }

        .input-icon {
            border: 0;
            position: absolute;
            left: 0;
            top: 0;
            z-index: 100;
            padding: 0 12px;
            line-height: 24px;

            .svg-fill {
                fill: $grey-4
            }

            .svg-stroke {
                stroke: $grey-4
            }
        }
    }
</style>