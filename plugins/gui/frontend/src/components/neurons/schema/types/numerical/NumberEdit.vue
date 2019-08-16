<script>
	import primitiveMixin from '../primitive.js'
    import numericalMixin from './numerical'
	import xSelect from '../../../../axons/inputs/Select.vue'
    import { validateNumber } from '../../../../../constants/validations'

    export default {
		name: 'x-number-edit',
        components: { xSelect },
        mixins: [primitiveMixin, numericalMixin],
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