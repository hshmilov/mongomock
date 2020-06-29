<script>
import primitiveMixin from '../../../../../mixins/primitive.js';
import numericalMixin from './numerical';
import XSelect from '../../../../axons/inputs/select/Select.vue';
import { validateNumber } from '../../../../../constants/validations';

export default {
  name: 'XNumberEdit',
  components: { XSelect },
  mixins: [primitiveMixin, numericalMixin],
  methods: {
    validateNumber,
    checkData() {
      if (isNaN(this.data)) return false;
      if (!this.schema.allow_negatives && this.data < 0) return false;
      if (this.schema.format === 'port' && this.data > 65536) return false;
      if (this.schema.max && this.data > this.schema.max) return false;
      return true;
    },
  },
};
</script>

<style lang="scss">

</style>
