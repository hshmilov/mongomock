<script>
	import PrimitiveMixin from '../primitive.js'
	import NumericalMixin from './numerical'

	export default {
		name: 'x-integer-edit',
        mixins: [PrimitiveMixin, NumericalMixin],
        methods: {
			formatData() {
				return parseInt(this.data)
            }
        }
	}
</script>

<style lang="scss">

</style>