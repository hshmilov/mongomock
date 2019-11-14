<script>
	import primitiveMixin from '../../../../../mixins/primitive.js'
	import numericalMixin from './numerical'
	import xSelect from '../../../../axons/inputs/Select.vue'
    import { validateInteger } from '../../../../../constants/validations'

    export default {
		name: 'XIntegerEdit',
        components: { xSelect },
        mixins: [primitiveMixin, numericalMixin],
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