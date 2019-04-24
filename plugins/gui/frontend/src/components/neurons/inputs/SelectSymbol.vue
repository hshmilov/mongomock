<template>
  <x-select
    v-bind="{options, value, placeholder, id, readOnly, searchable: true, size: 'sm'}"
    class="x-select-symbol"
    :class="{minimal}"
    @input="selectOption"
  >
    <template slot-scope="{ option }">
      <div class="x-type-img">
        <img
          v-if="type === 'img'"
          :src="require(`Logos/adapters/${option.name}.png`)"
          :alt="option.name"
        >
        <svg-icon
          v-else-if="type === 'icon'"
          :name="`navigation/${option.name}`"
          :original="true"
          width="30"
        />
      </div>
      <div class="logo-text">{{ option.title }}</div>
    </template>
  </x-select>
</template>

<script>
  import xSelect from '../../axons/inputs/Select.vue'

  export default {
    name: 'XSelectSymbol',
    components: { xSelect },
    props: {
      options: {
        type: Array,
        required: true
      },
      value: {
        type: String,
        default: ''
      },
      type: {
        type: String,
        default: 'img'
      },
      placeholder: {
        type: String,
        default: ''
      },
      id: {
        type: String,
        default: ''
      },
      minimal: Boolean,
      readOnly: Boolean
    },
    methods: {
      selectOption (option) {
        this.$emit('input', option)
      }
    }
  }
</script>

<style lang="scss">
    .x-select-symbol {
        .content {
            min-width: 100%;
        }

        .x-select-trigger {
            display: flex;
            align-items: center;
        }

        .x-type-img {
            width: 30px;
            line-height: 14px;
            text-align: center;
            display: inline-block;
            vertical-align: middle;

            img {
                max-width: 30px;
                max-height: 24px;
            }

            .svg-icon {
                .svg-stroke {
                    stroke: $grey-4;
                }

                .svg-fill {
                    fill: $grey-4;
                }
            }
        }

        .logo-text {
            max-width: 200px;
            margin-top: 2px;
            margin-left: 4px;
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
        }
        &.minimal .x-select-trigger .logo-text {
            display: none;
        }
    }
</style>