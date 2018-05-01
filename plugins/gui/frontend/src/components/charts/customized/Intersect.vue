<template>
    <x-pie :data="portionalData" @click-one="$emit('click-one', $event)" class="intersect" />
</template>

<script>
    import xPie from '../Pie.vue'

	export default {
		name: 'x-intersect',
        components: { xPie },
        props: { data: { required: true } },
        computed: {
			portionalData() {
				if (!this.data || !this.data.length) return []
                let total = this.data[0].count
                if (!total) return []
                return this.data.slice(1).map((item) => {
                    return { title: item.name, portion: item.count / total, anotate: true }
                })
            }
        }
	}
</script>

<style lang="scss">
</style>