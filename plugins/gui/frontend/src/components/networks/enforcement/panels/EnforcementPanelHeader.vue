<template>
  <ul>
    <li>
      <ATooltip
        title="Edit"
        placement="bottom"
      >
        <XIcon
          class="action-edit"
          family="action"
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
          family="action"
          type="remove"
          @click="$emit('delete')"
        />
      </ATooltip>
    </li>
  </ul>
</template>

<script>
import { Tooltip } from 'ant-design-vue';
import XIcon from '@axons/icons/Icon';

export default {
  name: 'XEnforcementPanelHeader',
  components: {
    ATooltip: Tooltip,
    XIcon,
  },
};
</script>

<style lang="scss">
  .action-edit, .action-remove {
    font-size: 20px;
    vertical-align: middle;
    color: #fff;
  }
</style>
