<template>
    <div>{{ formattedData }}</div>
</template>

<script>
	export default {
		name: 'x-string-view',
        props: ['schema', 'value'],
        data() {
			return {
				data: this.value
            }
        },
        computed: {
			formattedData() {
				if (this.schema.format === 'date-time') {
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