<template>
  <div class="x-color-picker">
    <div
      v-if="showPreset"
      v-click-outside="{
        exclude: ['colorButton'],
        handler: closePreset,
      }"
      class="x-color-picker__containter"
    >
      <SketchPicker
        :value="value || unselectedColor"
        :preset-colors="presetColors"
        disable-alpha
        @input="onChange"
      />
    </div>
    <div
      ref="colorButton"
      class="color-picker__trigger"
      :title="triggerButtonTitle"
      @mouseup="togglePreset"
    >
      <XIcon
        type="down"
        class="trigger__icon"
      />
      <span
        class="trigger__color"
        :style="triggerColorStyle"
      />
    </div>
  </div>
</template>

<script>
import { Sketch as SketchPicker } from 'vue-color';
import XIcon from '@axons/icons/Icon';
import { clickOutside } from '@directives/events';
import defaultChartsColors from '../../../constants/colors';

export default {
  name: 'XColorPicker',
  components: {
    SketchPicker,
    XIcon,
  },
  directives: {
    'click-outside': clickOutside,
  },
  props: {
    value: {
      type: String,
      default: undefined,
    },
    presetColors: {
      type: Array,
      default: () => ['#FF0000', '#00ff00', '#C94C4C', '#0000FF', '#84B84C'],
    },
  },
  data() {
    return {
      showPreset: false,
      unselectedColor: '#fff',
    };
  },
  computed: {
    triggerButtonTitle() {
      return !this.value ? 'Dynamic color - the slice color will be determined based on its size' : '';
    },
    triggerColorStyle() {
      return {
        backgroundColor: this.value || this.unselectedColor,
        border: !this.value ? `1px dashed ${defaultChartsColors.pieColors[0]}` : '',
      };
    },
  },
  methods: {
    onChange(v) {
      const selectedColorHEX = v.hex;
      this.$emit('input', selectedColorHEX);
    },
    togglePreset() {
      this.showPreset = !this.showPreset;
    },
    closePreset() {
      this.showPreset = false;
    },
  },
};
</script>

<style lang="scss">
.x-color-picker {
  display: inline-block;
  .color-picker__trigger {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 70px;
    height: 100%;
    border: solid 1px $grey-2;
    border-radius: 2px;
    cursor: pointer;
    .trigger__icon {
      font-size: 10px;
      color: #979797;
      margin-right: 14px;
    }
    .trigger__color {
      width: 23px;
      height: 22px;
      border-radius: 3px;
    }
  }
  &__containter {
    position: absolute;
    z-index: 1;
    top: 50%;
    right: 2%;
    transform: translate(-2%, -50%);
  }
}
</style>
