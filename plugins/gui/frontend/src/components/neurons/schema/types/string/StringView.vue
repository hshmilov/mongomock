<template>
    <img :src="value" v-if="schema.format && schema.format === 'image'" height="24" :style="{borderRadius: '50%'}" class="md-image">
    <img :src="require(`Logos/${value}.png`)" height="24"
         v-else-if="schema.format && schema.format === 'logo'" class="logo md-image">
    <svg-icon :name="`symbol/${value}`" :original="true" v-else-if="schema.format && schema.format === 'icon'" height="16" />
    <div v-else-if="hyperlink"><a :href="hyperlinkHref" @click="valueClicked(hyperlink)">{{ processedData }}</a></div>
    <div :class="{tag: schema.format && schema.format === 'tag'}" :title="completeData" v-else>{{ processedData }}</div>
</template>

<script>
    import HyperlinkMixin from '../hyperlink.js'

	export default {
		name: 'x-string-view',
        mixins: [HyperlinkMixin],
        props: ['schema', 'value'],
        computed: {
			processedData() {
				if (Array.isArray(this.value)) {
					let remainder = this.value.length - 2
					return this.value.slice(0, 2).map(item => this.format(item))
                        .join(', ') + (remainder > 0? ` +${remainder}`: '')
                }
                return this.format(this.value)
            },
            completeData() {
                if (Array.isArray(this.value)) {
                    return this.value.map(item => this.format(item)).join(', ')
                }
                return this.format(this.value)
            }
        },
        methods: {
			format(value) {
				if (!this.schema.format) return value
				if (this.schema.format.includes('date') || this.schema.format.includes('time')) {
					if (!value) return ''
					let dateTime = new Date(value)
					if (dateTime == 'Invalid Date') return value
                    dateTime.setMinutes(dateTime.getMinutes() - dateTime.getTimezoneOffset())
                    let dateParts = dateTime.toISOString().split('T')
					dateParts[1] = dateParts[1].split('.')[0]
                    if (this.schema.format === 'date') {
						return dateParts[0]
                    }
					if (this.schema.format === 'time') {
						return dateParts[1]
					}
					return dateParts.join(' ')
                }
				return value
            }
        }
	}
</script>

<style lang="scss">
</style>