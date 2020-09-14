<template functional>
  <div class="simple-pagination-wrapper">
    <XButton
      class="simple-pagination-wrapper__first"
      :disabled="props.page === 1"
      type="link"
      icon="double-left"
      title="First Page"
      @click="listeners['first']"
    />
    <slot />
    <XButton
      class="simple-pagination-wrapper__last"
      :disabled="props.page === $options.methods.calcPages(props.limit, props.total)"
      type="link"
      icon="double-right"
      title="Last Page"
      @click="($event) => listeners['last']($options.methods.calcPages(props.limit, props.total))"
    />
  </div>
</template>

<script>
export default {
  name: 'PaginatorFastNavWrapper',
  props: {
    page: {
      type: Number,
      default: 1,
    },
    total: {
      type: Number,
      required: true,
    },
    limit: {
      type: Number,
      default: 5,
    },
  },
  methods: {
    calcPages(limit, total) {
      const pages = Math.ceil(total / limit);
      return pages > 1 ? pages : 1;
    },
  },
};
</script>

<style lang="scss">
.simple-pagination-wrapper {
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: center;
  margin-bottom: 8px;
  .x-button {
    color: $grey-4;
    &:hover {
      color: $theme-blue
    }
    &:disabled {
      color: #d4d4d4;
    }
  }
}
</style>
