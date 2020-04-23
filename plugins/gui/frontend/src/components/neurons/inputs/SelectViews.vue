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
        <XSelect
          :value="view.name"
          :options="views[view.entity]"
          :searchable="true"
          placeholder="Query..."
          class="view-name"
          @input="updateName(index, $event)"
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
import XSelectSymbol from './SelectSymbol.vue';
import XSelect from '../../axons/inputs/select/Select.vue';
import XButton from '../../axons/inputs/Button.vue';

const dashboardView = { name: '', entity: '' };
export default {
  name: 'XSelectViews',
  components: {
    XSelectSymbol, XSelect, XButton,
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
    views: {
      type: Object,
      default: () => ({}),
    },
    max: {
      type: Number,
      default: 0,
    },
    min: {
      type: Number,
      default: 0,
    },
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
    updateName(index, name) {
      this.selected = this.selected.map((item, i) => {
        if (i === index) {
          item.name = name;
        }
        return item;
      });
    },
    updateEntity(index, entity) {
      this.selected = this.selected.map((item, i) => {
        if (i !== index) return item;
        return {
          entity, name: '',
        };
      });
    },
    removeView(index) {
      this.selected = this.selected.filter((_, i) => i !== index);
    },
    addView() {
      this.selected = [...this.selected, { ...dashboardView }];
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
    }
</style>
