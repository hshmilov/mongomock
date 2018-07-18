<template>
    <x-histogram :data="data" @click-one="$emit('click-one', $event)" :limit="5"/>
</template>

<script>
    import xHistogram from '../Histogram.vue'
	export default {
		name: 'x-compare',
        components: { xHistogram },
        props: {data: {required: true}}
	}
</script>

<style scoped>

</style>