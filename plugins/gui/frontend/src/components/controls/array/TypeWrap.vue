<template>
    <div class="object">
        <label v-if="label" :title="description" class="label"
               :for="name">{{label}}<div v-if="!required" class="hint">optional</div></label>
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'x-type-wrap',
        props: { name: {}, type: {}, description: {}, title: {}, required: { default: true } },
        computed: {
			label() {
				if (this.type === 'array') { return '' }
				return this.title
            }
        }
	}
</script>

<style lang="scss">
    .object {
        display: inline-block;
    }
</style>