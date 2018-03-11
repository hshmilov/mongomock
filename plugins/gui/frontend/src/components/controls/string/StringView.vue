<template>
    <img :src="value" v-if="schema.format && schema.format === 'image'">
    <img :src="`/src/assets/images/logos/${value}.png`" height="24px"
         v-else-if="schema.format && schema.format === 'logo'" class="logo">
    <div :class="{tag: schema.format && schema.format === 'tag'}" :title="formattedData"
         v-else>{{ formattedData }}</div>
</template>

<script>
	export default {
		name: 'x-string-view',
        props: ['schema', 'value'],
        computed: {
			formattedData() {
				if (this.schema.format === 'date-time') {
                    let dateTime = new Date(this.value)
                    if (dateTime == 'Invalid Date') return this.value

                    return `${dateTime.toLocaleDateString()} ${dateTime.toLocaleTimeString()}`
                } else if (Array.isArray(this.value)) {
					return this.value.join(', ')
                }
                return this.value
            }
        }
	}
</script>

<style lang="scss">

</style>