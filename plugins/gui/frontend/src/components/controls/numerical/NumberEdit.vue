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
            }
        }
	}
</script>

<style lang="scss">

</style>