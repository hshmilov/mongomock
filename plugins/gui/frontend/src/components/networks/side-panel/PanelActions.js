import Vue from 'vue';
import XIcon from '@axons/icons/Icon';

export const xActionsGroup = {
  name: 'XActionItem',
  render(h) {
    return (
      <ul>{this.$slots.default}</ul>
    );
  },
};

export const xActionItem = {
  name: 'XActionItem',
  components: ['XIcon'],
  props: {
    family: {
      type: String,
      default: '',
    },
    type: {
      type: String,
      required: true,
    },
    classList: {
      type: String,
      default: '',
    },
  },
  render(h) {
    return (
      <li onClick={() => this.$emit('click')}>
        <XIcon
          type={this.type}
          family={this.family}
          class={this.classList}
        />
      </li>
    );
  },
};
