import { mapState, mapActions } from 'vuex';
import { FETCH_DATA_FIELDS, SAVE_CUSTOM_DATA } from '@store/actions';
import _merge from 'lodash/merge';
import _get from 'lodash/get';
import _set from 'lodash/set';

export default {
  computed: {
    ...mapState({
      fields(state) {
        return state[this.module].fields.data;
      },
    }),
    genericSchema() {
      const schema = _get(this.fields, 'schema.generic');
      if (!schema) return null;
      return {
        ...schema,
      };
    },
    genericFieldNames() {
      return this.fields.generic.map((field) => field.name);
    },
    customFields() {
      return {
        predefined: this.fields.generic,
        custom: _get(this.fields, 'specific.gui', [])
          .filter((field) => !this.genericFieldNames.includes(field.name)),
      };
    },
  },
  methods: {
    ...mapActions({
      saveCustomData: SAVE_CUSTOM_DATA, fetchDataFields: FETCH_DATA_FIELDS,
    }),
    saveEntityCustomData(selection, data) {
      return this.saveCustomData({
        module: this.module,
        selection,
        data: this.prepareServerCustomData(data).reduce(this.mergeDuplicates, {}),
      });
    },
    prepareServerCustomData(customFieldsArray) {
      const res = customFieldsArray.map((item) => {
        if (item.name === 'specific_data.data.id') return { id: 'unique' };
        return this.convertGuiCustomData(item.name, item.value, item.predefined, item.title, {});
      });
      return res;
    },
    mergeDuplicates(data, item) {
      /**
       * If two nested fields exists, merge them.
       * for example, {'os': {'bitness': 32}} and {'os': {'type': 'windows'}} merge to -
       * {'os': {'bitness': 32, 'type': 'windows'}}
       */
      const key = Object.keys(item)[0];
      const realKey = key.replace('custom_', '');

      if (data[realKey]) {
        return { ...data, [realKey]: _merge(data[key], item[key]) };
      }
      return { ...data, [realKey]: item[key] };
    },
    convertGuiCustomData(name, value, predefined, title, result = {}) {
      /**
       * This method converts the custom fields into a proper object according to their schema.
       * for example, the pair {name: value} as {"specific_data.data.os.type" : "Windows"} will be converted into
       * {'os': {'type': 'Windows'}} - this is how the adapters save their data when fetched.
       * This is done only for predefined added fields and not custom fields.
       */
      if (name === 'specific_data.data.id') return result;
      if (!predefined) {
        return { ...result, [title || name]: value };
      }

      const remainingPath = this.trimName(name).split('.') || [];
      let currentPath = null;
      let currentSchema = this.genericSchema;
      let currentResult = result;

      while (remainingPath.length) {
        let found = false;
        for (let i = 0; i < currentSchema.items.length; i++) {
          const currentFieldName = remainingPath[0];
          if (currentSchema.items[i].name === currentFieldName) {
            currentPath = currentPath ? `${currentPath}.${currentFieldName}` : currentFieldName;
            remainingPath.shift();
            currentSchema = currentSchema.items[i];
            [currentResult, currentPath, currentSchema] = this.convertPathBySchemaStructure(
              currentPath, remainingPath, currentSchema, value, result,
            );
            found = true;
            break;
          }
        }
        if (!found) return { ...currentResult, [name]: value };
      }

      const fieldRootKey = Object.keys(currentResult)[0];
      return predefined
        ? { [fieldRootKey]: { predefined, value: currentResult[fieldRootKey] } }
        : { [fieldRootKey]: currentResult[fieldRootKey] };
    },
    convertPathBySchemaStructure(path, remainingPath, schema, value, result) {
      let currentPath = path;
      let pathIndex = 0;
      let currentSchema = schema;

      const existingValue = _get(result, currentPath);
      if (this.isComplexField(currentSchema)) {
        if (existingValue && existingValue.length) pathIndex = existingValue.length;
        currentPath += `[${pathIndex}]`;
        currentSchema = currentSchema.items;
        _set(result, currentPath, {});
      } else if (!remainingPath.length) {
        _set(result, currentPath, value);
      }
      return [result, currentPath, currentSchema];
    },
    isComplexField(currentSchema) {
      return currentSchema.type === 'array' && currentSchema.items.type === 'array';
    },
    trimName(name) {
      return name.replace(/(adapters_data|specific_data)\.(gui|data)\./g, '');
    },
    customUserField(name) {
      return name.startsWith('custom_');
    },
  },
};
