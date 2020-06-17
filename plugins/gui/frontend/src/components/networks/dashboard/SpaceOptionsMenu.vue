<template>
  <div>
    <ADropdown
      :trigger="['click']"
      placement="bottomRight"
      :get-popup-container="getPopupContainer"
    >
      <XButton
        class="action_trigger"
        type="link"
      >
        <XIcon
          type="thunderbolt"
        />Space Actions</XButton>
      <AMenu
        slot="overlay"
      >
        <AMenuItem
          v-if="editable"
          id="edit_space"
          key="0"
          @click="$emit('edit')"
        >
          Edit
        </AMenuItem>
        <AMenuItem
          v-if="removable"
          id="remove_space"
          key="1"
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
    editable: {
      type: Boolean,
      default: false,
    },
    removable: {
      type: Boolean,
      default: false,
    },
    parentSelector: {
      type: String,
      default: '',
    },
  },
  methods: {
    getPopupContainer() {
      if (this.parentSelector) {
        return document.querySelector(`.x-spaces .x-tabs ${this.parentSelector}`);
      }
      return undefined;
    },
  },
};
</script>

<style lang="scss">
.action_trigger {
  cursor: pointer;
  color: $theme-black;
  width: auto;
  padding-right: 0;
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
