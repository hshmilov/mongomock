<template>
    <div class="object">
        <label v-if="label" :title="description" class="label" :for="schema.name">{{label}}</label>
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'x-object',
        props: ['schema'],
        computed: {
			label() {
				if (this.schema.type === 'array') { return '' }
				return this.schema.title
            },
            description() {
				return this.schema.description || ''
            }
        }
	}
</script>

<style lang="scss">
</style>