<template>
  <div class="x-chart-metric">
    <label>Module for chart:</label>
    <XSelectSymbol
      id="module"
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      class="grid-span2"
      @input="updateEntity"
    />

    <label>Base query:</label>
    <XSelect
      id="baseQuery"
      v-model="base"
      :options="views[entity] || restrictedViewOptions(base)"
      :searchable="true"
      placeholder="query (or empty for all)"
      class="grid-span2 view-name"
    />

    <label>Intersecting query:</label>
    <XSelect
      id="intersectingFirst"
      :value="intersecting[0]"
      :options="views[entity] || restrictedViewOptions(intersecting[0])"
      :searchable="true"
      placeholder="query..."
      class="grid-span2"
      @input="(view) => updateIntersecting(0, view)"
    />
    <template v-if="intersecting.length > 1">
      <label>Intersecting query:</label>
      <XSelect
        id="intersectingSecond"
        :value="intersecting[1]"
        :options="views[entity] || restrictedViewOptions(intersecting[1])"
        :searchable="true"
        placeholder="query..."
        @input="(view) => updateIntersecting(1, view)"
      />
      <XButton
        type="link"
        @click="removeIntersecting(1)"
      >x</XButton>
    </template>
    <XButton
      type="light"
      :disabled="hasMaxViews"
      class="grid-span3"
      :title="addBtnTitle"
      @click="addIntersecting"
    >+</XButton>
  </div>
</template>

<script>
import XButton from '../../../axons/inputs/Button.vue';
import XSelect from '../../../axons/inputs/select/Select.vue';
import XSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue';
import chartMixin from './chart';

export default {
  name: 'XChartIntersect',
  components: { XButton, XSelect, XSelectSymbol },
  mixins: [chartMixin],
  data() {
    return {
      max: 2,
    };
  },
  computed: {
    initConfig() {
      return {
        entity: '', base: '', intersecting: ['', ''],
      };
    },
    entity: {
      get() {
        return this.config.entity;
      },
      set(entity) {
        this.config = { ...this.config, entity };
      },
    },
    base: {
      get() {
        return this.config.base;
      },
      set(base) {
        this.config = { ...this.config, base };
      },
    },
    intersecting: {
      get() {
        return this.config.intersecting;
      },
      set(intersecting) {
        this.config = { ...this.config, intersecting: [...intersecting] };
      },
    },
    hasMaxViews() {
      if (!this.max) return false;
      return this.intersecting.length === this.max;
    },
    addBtnTitle() {
      return this.hasMaxViews ? `Limited to ${this.max} intersecting queries` : '';
    },
  },
  methods: {
    updateEntity(entity) {
      if (entity === this.entity) return;
      this.config = {
        entity,
        base: '',
        intersecting: ['', ''],
      };
    },
    removeIntersecting(index) {
      this.intersecting.splice(index, 1);
      this.intersecting = [...this.intersecting];
    },
    addIntersecting() {
      this.intersecting = [...this.intersecting, ''];
    },
    updateIntersecting(index, view) {
      this.intersecting = this.intersecting.map((item, ind) => {
        if (ind === index) return view;
        return item;
      });
    },
    validate() {
      this.$emit('validate', !this.intersecting.filter((view) => view === '').length);
    },
    restrictedViewOptions(selectedView) {
      if (!this.entity || !selectedView) {
        return [];
      }
      return [{
        name: selectedView, title: 'Missing Permissions',
      }];
    },
  },
};
</script>

<style lang="scss">

</style>
