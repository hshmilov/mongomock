<template>
  <ul>
    <li>
      <ATooltip
        title="Edit"
        placement="bottom"
      >
        <XIcon
          class="action-edit"
          type="edit"
          @click="$emit('edit')"
        />
      </ATooltip>
    </li>
    <li>
      <ATooltip
        title="Delete"
        placement="bottom"
      >
        <XIcon
          class="action-remove"
          type="delete"
          @click="$emit('delete')"
        />
      </ATooltip>
    </li>
  </ul>
</template>

<script>
import { Tooltip } from 'ant-design-vue';

export default {
  name: 'XEnforcementPanelHeader',
  components: {
    ATooltip: Tooltip,
  },
};
</script>

<style lang="scss">
</style>
