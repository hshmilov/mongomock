export default {
  props: {
    value: {},
    entities: {
      type: Array,
      required: true,
    },
    viewOptions: {
      type: Function,
      required: true,
    },
    chartView: {
      type: String,
      required: true,
    },
  },
  computed: {
    config: {
      get() {
        if (this.value) return this.value;
        return { ...this.initConfig };
      },
      set(newConfig) {
        this.$emit('input', newConfig);
        this.$nextTick(this.validate);
      },
    },
  },
};
