<template>
    <div>{{ data.length }} Bytes</div>
</template>

<script>
	export default {
		name: 'x-array-view',
        props: ['schema', 'value'],
        data() {
			return {
				data: [ ...this.value ]
            }
        }
	}
</script>

<style lang="scss">

</style>