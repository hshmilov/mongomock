<template>
  <div class="x-select-views">
    <div
      ref="queries"
      class="queries"
    >
      <div
        v-for="(view, index) in value"
        :key="index"
        class="view"
      >
        <XSelectSymbol
          :value="view.entity"
          :options="entities"
          type="icon"
          placeholder="Module..."
          @input="updateEntity(index, $event)"
        />
        <div class="grid-span2 field-with-colors-bar">
          <XSelect
            :value="view.id"
            :options="viewOptions(view.entity, view.id)"
            :searchable="true"
            placeholder="Query..."
            class="view-name"
            @input="updateId(index, $event)"
          />
          <XColorPicker
            class="color-picker-container"
            :value="view.chart_color || (defaultChartColors.length ?
              defaultChartColors[index % defaultChartColors.length] : colorPickerPreset[0])"
            :preset-colors="colorPickerPreset"
            @input="updateColorValue(index, $event)"
          />
          <XButton
            v-if="isItemDeletable(index)"
            type="link"
            class="add_query"
            @click="removeView(index)"
          >x</XButton>
          <div
            v-else
          />
        </div>
      </div>
    </div>
    <XButton
      id="add_view"
      type="light"
      :disabled="hasMaxViews"
      :title="addBtnTitle"
      @click="addView"
    >+</XButton>
  </div>
</template>

<script>
import XColorPicker from '@axons/inputs/ColorPicker.vue';
import defaultChartsColors from '../../../constants/colors';
import XSelectSymbol from './SelectSymbol.vue';
import XSelect from '../../axons/inputs/select/Select.vue';
import XButton from '../../axons/inputs/Button.vue';

const viewTemplate = { id: '', entity: '' };
export default {
  name: 'XSelectViews',
  components: {
    XSelectSymbol, XSelect, XButton, XColorPicker,
  },
  props: {
    value: {
      type: Array,
      default: () => ([]),
    },
    entities: {
      type: Array,
      required: true,
    },
    viewOptions: {
      type: Function,
      required: true,
    },
    max: {
      type: Number,
      default: 0,
    },
    min: {
      type: Number,
      default: 0,
    },
    defaultChartColors: {
      type: Array,
      default: () => [],
    },
    chartView: {
      type: String,
      default: '',
    },
    intersection: {
      type: Boolean,
    },
  },
  data() {
    return {
      colorPickerPreset: defaultChartsColors.pieColors,
    };
  },
  computed: {
    selected: {
      get() {
        return this.value;
      },
      set(selected) {
        this.$emit('input', selected);
      },
    },
    addBtnTitle() {
      return this.hasMaxViews ? `Limited to ${this.max} queries` : '';
    },
    hasMaxViews() {
      if (!this.max || !this.selected) return false;
      return this.selected.length === this.max;
    },
  },
  methods: {
    updateId(index, id) {
      this.selected = this.selected.map((item, i) => {
        if (i !== index) {
          return item;
        }
        return {
          ...item,
          id,
        };
      });
    },
    updateEntity(index, entity) {
      this.selected = this.selected.map((item, i) => {
        if (i !== index) {
          return item;
        }
        return {
          entity,
          id: '',
        };
      });
    },
    updateColorValue(index, color) {
      this.selected = this.selected.map((item, i) => {
        if (i !== index) {
          return item;
        }
        return {
          ...item,
          chart_color: color,
        };
      });
    },
    removeView(index) {
      this.selected = this.selected.filter((_, i) => i !== index);
    },
    addView() {
      this.selected = [...this.selected, { ...viewTemplate }];
      this.$nextTick(() => {
        const ref = this.$refs.queries;
        ref.scrollTop = ref.scrollHeight;
      });
    },
    isItemDeletable(index) {
      return index >= this.min;
    },
  },
};
</script>

<style lang="scss">
    .x-select-views {
      .queries {
        max-height: 200px;
        @include  y-scrollbar;
        overflow-x: hidden;
        overflow-y: auto;
      }
      .view {
        display: grid;
        grid-template-columns: 160px auto 35px;
        grid-gap: 0 8px;
        min-width: 0;
        margin: 8px 0;
        &:last-child{
          margin: 0;
        }
      }
      .x-button {
        margin-top: 8px;
      }
      .field-with-colors-bar {
        display: flex;
        .x-dropdown{
          max-width: calc(100% - 114px);
        }
        .color-picker-container {
          margin-left: 5px;
        }
      }
      .view-name{
        width: 100%;
      }
    }
</style>
