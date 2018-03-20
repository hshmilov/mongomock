<template>
    <div class="custom-data" :style="{gridTemplateColumns: gridCols}">
        <template v-if="isObject && isArray">
            <div v-for="item, i in data">
                <div v-if="data.length > 1" class="index">{{ i + 1 }}.</div>
                <x-custom-data :data="item"/>
            </div>
        </template>
        <template v-else-if="isObject">
            <div v-for="key in Object.keys(data)">
                <x-type-wrap :title="key" :class="{title: (typeof data[key] === 'object')}" :required="true">
                    <x-custom-data :data="data[key]"/>
                </x-type-wrap>
            </div>
        </template>
        <template v-else>{{ data }}</template>
    </div>
</template>

<script>
	import xTypeWrap from '../controls/array/TypeWrap.vue'

	export default {
		name: 'x-custom-data',
		components: {xTypeWrap},
        props: {data: {required: true}},
        computed: {
			isObject() {
				return this.data && typeof this.data === 'object'
            },
            isArray() {
				return this.data && Array.isArray(this.data)
            },
            gridCols() {
                if (!this.data || !this.isObject || this.isArray) return 'none'

                let foundObjChild = false
                return Object.keys(this.data).filter((key) => {
                	if (!foundObjChild && typeof this.data[key] !== 'object') return true
                    foundObjChild = true
                    return false
				}).map(() => {
                	return '1fr'
                }).join(' ')
            }
        }
	}
</script>

<style lang="scss">
    .custom-data {
        display: grid;
        grid-gap: 12px;
        .label {
            font-weight: 500;
        }
        .index {
            float: left;
            margin-right: 12px;
        }
        .title > label {
            text-decoration: underline;
        }
    }
</style>