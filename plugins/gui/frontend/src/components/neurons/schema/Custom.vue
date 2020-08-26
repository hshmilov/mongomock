<template>
  <div class="x-schema-custom">
    <template v-if="isObject && isArray">
      <div
        v-for="(item, i) in data"
        :key="i"
      >
        <div
          v-if="data.length > 1"
          class="index"
        >{{ i + 1 }}.</div>
        <XSchemaCustom :data="item" />
      </div>
    </template>
    <template v-else-if="isObject">
      <div
        v-for="key in Object.keys(data)"
        :key="key"
      >
        <XTypeWrap
          :title="key.split('_').join(' ')"
          :class="{title: (typeof data[key] === 'object')}"
          :required="true"
        >
          <XSchemaCustom :data="data[key]" />
        </XTypeWrap>
      </div>
    </template>
    <div
      v-else
      class="x-schema-custom__content"
    >{{ data }}</div>
  </div>
</template>

<script>
import XTypeWrap from './types/array/TypeWrap.vue';

export default {
  name: 'XSchemaCustom',
  components: {
    XTypeWrap,
  },
  props: {
    data: {
      type: [Object, String, Number, Boolean],
      required: true,
    },
    vertical: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    isObject() {
      return this.data && typeof this.data === 'object';
    },
    isArray() {
      return this.data && Array.isArray(this.data);
    },
  },
};
</script>

<style lang="scss">
  .x-schema-custom {
    display: grid;
    grid-gap: 12px;

    &__content {
      // In case data has inner whitespaces
      white-space: pre;
    }

    .label {
      font-weight: 500;
    }

    .index {
      float: left;
      margin-right: 12px;
    }

    .title > label {
      text-decoration: underline;
      text-transform: capitalize;
    }
  }
</style>
