<script>
	import PrimitiveMixin from '../primitive.js'
    import NumericalMixin from './numerical'

	export default {
		name: 'x-number-edit',
        mixins: [PrimitiveMixin, NumericalMixin],
        methods: {
			formatData() {
				return parseFloat(this.data)
            }
        }
	}
</script>

<style lang="scss">

</style>