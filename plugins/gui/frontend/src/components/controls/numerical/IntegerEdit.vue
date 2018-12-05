<script>
	import PrimitiveMixin from '../primitive.js'
	import NumericalMixin from './numerical'
	import xSelect from '../../inputs/Select.vue'
    import { validateInteger } from '../../../utils'

    export default {
		name: 'x-integer-edit',
        mixins: [PrimitiveMixin, NumericalMixin],
        components: { xSelect },
        methods: {
		    validateNumber: validateInteger,
			formatData() {
				if (this.data === '-' || this.data === '') {
					return this.data
				}
				return parseInt(this.data)
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