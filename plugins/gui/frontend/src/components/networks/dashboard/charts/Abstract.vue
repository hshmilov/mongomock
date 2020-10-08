<template>
  <div class="x-chart-metric">
    <XSelectSymbol
      :value="entity"
      :options="entities"
      type="icon"
      placeholder="module..."
      @input="updateEntity"
    />
    <XSelect
      v-model="view"
      :options="currentViewOptions"
      :searchable="true"
      placeholder="query (or empty for all)"
    />
    <div />
    <div />
    <XSelectTypedField
      v-model="fieldName"
      :options="fieldOptions"
    />
    <div />
    <div />
    <XSelect
      v-model="func"
      :options="funcOptions"
      placeholder="function..."
    />
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import { isTableField } from '@constants/utils';
import XSelect from '../../../axons/inputs/select/Select.vue';
import XSelectSymbol from '../../../neurons/inputs/SelectSymbol.vue';
import XSelectTypedField from '../../../neurons/inputs/SelectTypedField.vue';
import chartMixin from './chart';
import { GET_MODULE_SCHEMA, GET_DATA_SCHEMA_BY_NAME } from '../../../../store/getters';

export default {
  name: 'XChartAbstract',
  components: { XSelect, XSelectSymbol, XSelectTypedField },
  mixins: [chartMixin],
  computed: {
    ...mapGetters({
      getModuleSchema: GET_MODULE_SCHEMA, getDataSchemaByName: GET_DATA_SCHEMA_BY_NAME,
    }),
    initConfig() {
      return {
        entity: '', view: '', field: { name: '' }, func: '',
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
    view: {
      get() {
        return this.config.view;
      },
      set(view) {
        this.config = { ...this.config, view };
      },
    },
    fieldName: {
      get() {
        return this.config.field.name;
      },
      set(fieldName) {
        let field = { name: '' };
        if (this.schemaByName[fieldName]) {
          field = this.schemaByName[fieldName];
        }
        this.config = { ...this.config, field };
      },
    },
    func: {
      get() {
        return this.config.func;
      },
      set(func) {
        this.config = { ...this.config, func };
      },
    },
    funcOptions() {
      return [
        { name: 'average', title: 'Average' },
        { name: 'count', title: 'Count' },
      ];
    },
    fieldOptions() {
      if (!this.entity) return [];
      return this.getModuleSchema(this.entity).map((category) => ({
        ...category,
        fields: category.fields.filter((field) => {
          if (!isTableField(field.name)) return false;
          return !field.branched && field.type !== 'array'
                && (this.func !== 'average' || field.type === 'number' || field.type === 'integer');
        }),
      }));
    },
    schemaByName() {
      if (!this.entity) return {};
      return this.getDataSchemaByName(this.entity);
    },
    currentViewOptions() {
      return this.viewOptions(this.entity, this.view);
    },
  },
  methods: {
    validate() {
      this.$emit('validate', this.fieldName && this.func);
    },
    updateEntity(entity) {
      if (this.entity === entity) return;
      this.config = {
        ...this.config,
        entity,
        view: '',
      };
    },
  },
};
</script>
