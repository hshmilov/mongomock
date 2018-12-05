<script>
	import PrimitiveMixin from '../primitive.js'
    import NumericalMixin from './numerical'
	import xSelect from '../../inputs/Select.vue'
    import { validateNumber } from '../../../utils'

    export default {
		name: 'x-number-edit',
        components: { xSelect },
        mixins: [PrimitiveMixin, NumericalMixin],
        methods: {
		    validateNumber,
			formatData() {
                if (this.data === '-' || this.data === '') {
			        return this.data
                }
				return parseFloat(this.data)
            },
			checkData() {
				if (isNaN(this.data)) return false
                if (!this.schema.allow_negatives && this.data < 0) return false
                if (this.schema.format === 'port' && this.data > 65536) return false
				return true
			}
        }
	}
</script>

<style lang="scss">

</style>