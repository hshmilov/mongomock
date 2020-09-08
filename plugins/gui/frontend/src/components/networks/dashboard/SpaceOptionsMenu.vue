<template>
  <div>
    <ADropdown
      :trigger="['click']"
      placement="bottomCenter"
    >
      <XButton
        class="action-trigger"
        type="link"
      >
        <XIcon
          family="symbol"
          type="verticalDots"
        />
      </XButton>
      <AMenu
        slot="overlay"
        :style="{minWidth: '80px'}"
      >
        <AMenuItem
          v-if="editable"
          id="edit_space"
          key="1"
          @click="$emit('edit')"
        >
          Edit
        </AMenuItem>
        <AMenuItem
          v-if="removable"
          id="remove_space"
          key="2"
          @click="$emit('remove')"
        >
          Delete
        </AMenuItem>
      </AMenu>
    </ADropdown>
  </div>
</template>

<script>
import { Menu, Dropdown } from 'ant-design-vue';
import XIcon from '@axons/icons/Icon';
import XButton from '@axons/inputs/Button.vue';

export default {
  name: 'XSpaceOptionsMenu',
  components: {
    ADropdown: Dropdown,
    AMenu: Menu,
    AMenuItem: Menu.Item,
    XButton,
    XIcon,
  },
  props: {
    supportedActions: {
      type: Array,
      default: () => [],
    },
  },
  computed: {
    removable() {
      return this.supportedActions.includes('remove');
    },
    editable() {
      return this.supportedActions.includes('edit');
    },
  },
};
</script>

<style lang="scss">
.action-trigger {
  cursor: pointer;
  color: $theme-black;
  width: auto;
  padding-right: 0;
  .x-icon {
    font-size: 16px;
  }
  svg {
    stroke: $theme-black;
  }
  &:visited, &:focus {
    color: $theme-black;
    svg {
      stroke: $theme-black;
    }
  }
  &:hover, &.ant-dropdown-open {
     color: $theme-blue;
     svg {
       stroke: $theme-blue;
     }
  }
}
</style>
