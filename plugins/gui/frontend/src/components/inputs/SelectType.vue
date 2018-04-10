<template>
    <x-select :options="options" :value="value" @input="selectOption" class="x-select-type">
        <template slot-scope="{ option }">
            <div class="x-type-img"><img :src="`/src/assets/images/logos/${option.name}.png`" /></div>
            <div class="logo-text">{{option.title}}</div>
        </template>
    </x-select>
</template>

<script>
    import xSelect from './Select.vue'

	export default {
		name: 'x-select-type',
        components: { xSelect },
        props: { options: {required: true}, value: {}},
        methods: {
			selectOption(option) {
				this.$emit('input', option)
            }
        }
	}
</script>

<style lang="scss">
    .x-select-type {
        .x-type-img {
            width: 30px;
            height: 24px;
            text-align: center;
            display: inline-block;
            img {
                margin: auto;
                max-width: 30px;
                max-height: 24px;
            }
        }
        .logo-text {
            max-width: 160px;
        }
    }
</style>