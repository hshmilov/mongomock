<template>
  <XSelect
    v-bind="{options, value, size: 'sm'}"
    class="x-select-symbol"
    @input="selectOption"
  >
    <template slot-scope="{ option }">
      <div class="x-type-img">
        <img
          :src="require(`Logos/adapters/${option.name}_adapter.png`)"
          :alt="option.name"
        >
      </div>
      <div
        v-if="option"
        class="logo-text"
      >
        {{ option.title }}
      </div>
    </template>
  </XSelect>
</template>


<script>
import XSelect from '../../axons/inputs/select/Select.vue';

export default {
  name: 'XComplianceSelect',
  components: { XSelect },
  props: {
    options: {
      type: Array,
      required: true,
    },
    value: {
      type: [String, Object],
      default: null,
    },
    type: {
      type: String,
      default: 'img',
    },
  },
  methods: {
    selectOption(value) {
      this.$emit('input', value);
    },
  },
};
</script>

<style scoped lang="scss">
    .x-select-symbol {

        .x-type-img {
            width: 30px;
            line-height: 14px;
            text-align: center;
            display: inline-block;
            vertical-align: middle;
            margin-left: 2px;

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
            margin-top: 2px;
            margin-left: 10px;
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
            max-width: 420px;
        }
    }
</style>
