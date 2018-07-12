<template>
    <img :src="value" v-if="schema.format && schema.format === 'image'" height="24" :style="{borderRadius: '50%'}">
    <img :src="`/src/assets/images/logos/${value}.png`" height="24"
         v-else-if="schema.format && schema.format === 'logo'" class="logo">
    <svg-icon :name="`symbol/${value}`" :original="true" v-else-if="schema.format && schema.format === 'icon'" height="16"></svg-icon>
    <div :class="{tag: schema.format && schema.format === 'tag'}" :title="processedData" v-else>{{ processedData }}</div>
</template>

<script>
	export default {
		name: 'x-string-view',
        props: ['schema', 'value'],
        computed: {
			processedData() {
				if (Array.isArray(this.value)) {
					let remainder = this.value.length - 2
					return this.value.slice(0, 2).map(item => this.format(item))
                        .join(', ') + (remainder > 0? ` +${remainder}`: '')
                }
                return this.format(this.value)
            }
        },
        methods: {
			format(value) {
				if (this.schema.format === 'date-time') {
					if (!value) return ''
					let dateTime = new Date(value)
					if (dateTime === 'Invalid Date') return value

					return `${dateTime.toLocaleDateString()} ${dateTime.toLocaleTimeString()}`
				} else if (this.schema.format === 'time') {
					if (!value) return ''
					let dateTime = new Date(value)
					if (dateTime === 'Invalid Date') return value

					return dateTime.toLocaleTimeString()
                }
				return value
            }
        }
	}
</script>

<style lang="scss">
</style>