<template>
  <div
    class="expression-actions"
  >
    <XButton
      :disabled="disabledToggleField"
      type="link"
      class="expression-toggle-column"
      :title="isColumnInTable ? 'Remove Field from Columns' : 'Add Field to Columns'"
      @click="$emit('toggle-column')"
    >
      <XIcon
        family="action"
        :type="isColumnInTable ? 'removeColumn' : 'addColumn'"
      />
    </XButton>
    <XButton
      type="link"
      class="expression-duplicate"
      title="Duplicate Row"
      @click="$emit('duplicate')"
    >
      <XIcon
        family="action"
        type="duplicateRow"
      />
    </XButton>
    <XButton
      type="link"
      class="expression-remove"
      title="Remove Expression"
      @click="$emit('remove')"
    >
      <XIcon
        type="close"
      />
    </XButton>
  </div>
</template>

<script>
export default {
  name: 'XExpressionActions',
  props: {
    isColumnInTable: {
      type: Boolean,
      default: false,
    },
    disabledToggleField: {
      type: Boolean,
      default: false,
    },
  },
};
</script>
<style lang="scss">
.expression-actions {
  display: flex;
  .x-button {
    padding-right: 1px;
    padding-left: 1px;
  }
  .expression-remove {
    padding-top: 3px;
    padding-left: 0px;
  }
  .expression-duplicate, .child-duplicate,
  .expression-toggle-column, .child-toggle-column {
    font-size: 20px;
    .x-icon {
      display: block;
    }
  }
}
</style>
