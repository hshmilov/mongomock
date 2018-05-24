<script>
	import PrimitiveMixin from '../primitive.js'
    import NumericalMixin from './numerical'
	import xSelect from '../../inputs/Select.vue'

	export default {
		name: 'x-number-edit',
        components: { xSelect },
        mixins: [PrimitiveMixin, NumericalMixin],
        methods: {
			formatData() {
				return parseFloat(this.data)
            },
			checkData() {
				if (isNaN(this.data) || this.data <= 0) return false
                if (this.schema.format === 'port' && this.data > 65536) return false
				return true
			}
        }
	}
</script>

<style lang="scss">

</style>