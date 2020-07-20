export default {
  data() {
    return {
      isActive: false,
    };
  },
  props: {
    entities: {
      type: Object,
      required: true,
      default: () => ({}),
    },
    module: {
      type: String,
      required: true,
      default: '',
    },
    selectionCount: {
      type: Number,
      default: 0,
    },
    entitiesMeta: {
      type: Object,
      default: () => {},
    },
  },
  methods: {
    activate() {
      this.isActive = true;
    },
  },
};
