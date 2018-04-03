<script>
	import PrimitiveMixin from '../primitive.js'
	import NumericalMixin from './numerical'
	import xSelect from '../../inputs/Select.vue'

	export default {
		name: 'x-integer-edit',
        mixins: [PrimitiveMixin, NumericalMixin],
        components: { xSelect },
        methods: {
			formatData() {
				return parseInt(this.data)
            }
        }
	}
</script>

<style lang="scss">

</style>