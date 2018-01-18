<template>
    <div class="object-item" v-if="hasAnyData">
        <label v-if="schema.title && schema.type !== 'array'" :title="schema.description || ''" class="data-label"
               :for="schema.name">{{schema.title}}:</label>
        <component :is="schema.type" v-bind="schema" :data="data" :id="schema.name" class="object-data"></component>
    </div>
</template>

<script>
    import String from './String.vue'
    import Number from './Number.vue'
    import Boolean from './Boolean.vue'

	export default {
		name: 'object-schema',
        components: { String, Number, Boolean },
        props: ['schema', 'data'],
        computed: {
			hasAnyData() {
				let hasValue = false;
				Object.values(this.data).forEach((value) => {
					if (value) {
						hasValue = true;
                    }
                })
                return hasValue;
            }
        }
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .object-item {
        .data-label {
            color: $color-theme-light;
            text-decoration: underline;
        }
        display: inline-block;
        .object-data {
            display: inline-block;
        }
    }
</style>