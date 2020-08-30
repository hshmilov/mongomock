<template>
  <div
    class="x-trigger"
    @click="!readOnly && $emit('click')"
  >
    <XTextBox v-bind="{id, text, selected, clickable: !readOnly}">
      <template slot="logo">
        <img
          v-if="title"
          :src="require('Logos/actions/trigger.png')"
          class="md-image logo"
        >
        <div
          v-else
          class="logo placeholder"
          :class="{disabled: readOnly}"
        >
          +
        </div>
      </template>
    </XTextBox>
  </div>
</template>

<script>
import XTextBox from '../../axons/layout/TextBox.vue';

export default {
  name: 'XTrigger',
  components: { XTextBox },
  props: {
    id: {
      type: String,
      default: '',
    },
    title: {
      type: String,
      default: '',
    },
    selected: {
      type: Boolean,
      default: false,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    text() {
      if (this.title) return this.title;

      return 'Trigger';
    },
  },
};
</script>

<style lang="scss">
    .x-trigger {
        display: flex;
        .logo {
            height: 48px;
            &.placeholder {
                background-color: rgba($theme-orange, 0.2);
                min-width: 48px;
                border-radius: 50%;
                line-height: 48px;
                text-align: center;
                font-size: 36px;
            }
            &.placeholder.disabled {
              background-color: $grey-3;
            }
        }
    }
</style>
