/*
Common functionality for array typed controls.
Received props include:
- schema - parameters configuring the functionality of the array.
           Specifically, expected to contain 'items' describing types of children,
           either unified for a regular array or a tuple representing an ordered object.
- value - data in the form of object, where keys are numbers (for a unified array)
          or names of items (for a tuple representing an ordered object)
 */
import _isObject from 'lodash/isObject';

export default {
  props: {
    schema: { required: true }, value: { required: true }, apiUpload: {},
  },
  computed: {
    data: {
      get() {
        return this.value || [];
      },
      set(value) {
        this.$emit('input', value);
      },
    },
    isOrderedObject() {
      return Array.isArray(this.schema.items);
    },
    processedData() {
      return this.data;
    },
    required() {
      return this.schema.required;
    },
    schemaItems() {
      // Process schema to create list of items which Array components can present
      if (this.isOrderedObject) {
        // schema.items contains explicit definition for each type of contained children
        // Filter those without a 'title' property and are not of type 'array' since they are not for presentation
        return this.schema.items.filter((item) => (item.title || item.type === 'array') && !item.hidden);
      }
      if (_isObject(this.schema.items) && this.schema.name) {
        // schema.items contains one unified definition for type of all children
        return this.toList(this.processedData)
        // Use same unified schema and add name
          .map((item, index) => ({ ...this.schema.items, name: index }));
      }
      if (!this.schema.items) {
        // schema contains one unified definition for all data elements (primitive containing array)
        return this.toList(this.processedData)
        // Use same unified schema and add name
          .map((item, index) => ({ ...this.schema, name: index, title: undefined }));
      }
      return [];
    },
    processedSchemaItems() {
      return this.schemaItems.map((field) => {
        let {
          type, required, hyperlinks,
        } = field;
        const { name, items } = field;
        if (this.isFile(field)) {
          type = 'file';
        }
        // Primitive children are required if appear in schema.required list
        if (type !== 'array' || (items && items.type === 'string')) {
          const isFieldRequired = Array.isArray(this.required) && this.required.includes(name);
          required = this.required === true || isFieldRequired;
        }
        if (this.schema.hyperlinks) {
          hyperlinks = this.schema.hyperlinks;
          if (field.name && typeof field.name === 'string') {
            const cleanName = field.name.replace('specific_data.', '').replace('data.', '');
            hyperlinks = cleanName ? hyperlinks[cleanName] : hyperlinks;
          }
        }
        return {
          ...field,
          type,
          required,
          hyperlinks,
          filter: this.schema.filter,
        };
      });
    },
    dataSchemaItems() {
      const data = this.processedData;
      return this.processedSchemaItems
        .filter((schema) => !this.empty(data[schema.name]))
        .map((schema) => ({
          schema, data: data[schema.name],
        }));
    },
    isHidden() {
      return this.data.enabled === false;
    },
    conditionalItem() {
      return this.schemaItems.find((item) => item.name === 'conditional');
    },
    conditionalItemOptions() {
      return this.conditionalItem
        ? this.conditionalItem.enum.map((option) => option.name)
        : [];
    },
    conditionalSelection() {
      return this.data.conditional;
    },
    shownSchemaItems() {
      if (this.isHidden) {
        return this.processedSchemaItems.filter((x) => x.name === 'enabled');
      }
      if (this.conditionalItem) {
        const isIndependent = (name) => !this.conditionalItemOptions.includes(name);
        const isSelected = (name) => name === this.conditionalSelection;
        const isIndependentOrSelected = ({ name }) => isIndependent(name) || isSelected(name);
        return this.processedSchemaItems.filter(isIndependentOrSelected);
      }
      return this.processedSchemaItems;
    },
  },
  data() {
    return {
      collapsed: false,
    };
  },
  methods: {
    empty(data) {
      if (data === undefined || data == null || data === '') return true;
      if (typeof data !== 'object') return false;
      const dataToCheck = Array.isArray(data) ? data : Object.values(data);
      let hasValue = false;
      dataToCheck.forEach((value) => {
        if (value !== undefined && value !== null && value !== '') {
          hasValue = true;
        }
      });
      return !hasValue;
    },
    toList(data) {
      if (!data) return [];
      if (!Array.isArray(data)) {
        return Object.keys(data);
      }
      return data;
    },
    isFile(schema) {
      return (schema.type === 'file');
    },
  },
};
