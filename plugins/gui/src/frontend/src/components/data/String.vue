<template>
    <div>{{ formattedData }}</div>
</template>

<script>
	export default {
		name: 'string',
        props: ['format', 'data'],
        computed: {
			formattedData() {
				if (this.format === 'date-time') {
                    let dateTime = new Date(this.data)
                    return `${dateTime.toLocaleDateString()} ${dateTime.toLocaleTimeString()}`
                }
                return this.data
            }
        }

	}
</script>

<style lang="scss">

</style>