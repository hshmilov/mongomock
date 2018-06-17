<template>
    <x-pie :data="portionalData" @click-one="$emit('click-one', $event)" :id="id" class="intersect" />
</template>

<script>
    import xPie from '../Pie.vue'

	export default {
		name: 'x-intersect',
        components: { xPie },
        props: { data: { required: true }, id: {} },
        computed: {
			portionalData() {
				if (!this.data || !this.data.length) return []
                let total = this.data[0].count
                if (!total) return []
                return this.data.slice(1).map((item, index) => {
                    let newItem = { title: item.name, portion: item.count / total, anotate: true }
                    if (index === 1) {
                    	newItem.class = 'fill-intersection-1-2'
                    } else {
						newItem.class = `extra-fill-${(index % 6) + 1}`
                    }
                    return newItem
                })
            }
        }
	}
</script>

<style lang="scss">
</style>