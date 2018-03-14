<template>
    <img :src="value" v-if="schema.format && schema.format === 'image'" height="24" :style="{borderRadius: '50%'}">
    <img :src="`/src/assets/images/logos/${value}.png`" height="24"
         v-else-if="schema.format && schema.format === 'logo'" class="logo">
    <div :class="{tag: schema.format && schema.format === 'tag'}" :title="processedData"
         v-else>{{ processedData }}</div>
</template>

<script>
	export default {
		name: 'x-string-view',
        props: ['schema', 'value'],
        computed: {
			processedData() {
				if (Array.isArray(this.value)) {
					return this.value.map(item => this.format(item)).join(', ')
                }
                return this.format(this.value)
            }
        },
        methods: {
			format(value) {
				if (this.schema.format === 'date-time') {
					let dateTime = new Date(value)
					if (dateTime == 'Invalid Date') return value

					return `${dateTime.toLocaleDateString()} ${dateTime.toLocaleTimeString()}`
				}
				return value
            }
        }
	}
</script>

<style lang="scss">

</style>