<template>
    <div class="object">
        <label v-if="label" :title="description" class="label" :for="name">{{label}}</label>
        <slot></slot>
    </div>
</template>

<script>
	export default {
		name: 'x-type-wrap',
        props: ['name', 'type', 'description', 'title'],
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
        .label {  margin-bottom: 0;  }
    }
</style>