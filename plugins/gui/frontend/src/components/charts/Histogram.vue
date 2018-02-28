<template>
    <div class="histogram">
        <div v-for="name in dataNamesTruncated" class="histogram-item">
            <div class="quantity">{{data[name]}}</div>
            <div class="bar" :style="{height: calculateBarHeight(data[name]) + 'px'}">
                <img :src="`/src/assets/images/logos/${name}.png`" width="16">
            </div>
        </div>
        <div v-if="dataNames.length > limit" class="remainder">+{{dataNames.length - limit}}</div>
    </div>
</template>

<script>

	export default {
		name: 'x-histogram',
		props: {data: {required: true}, limit: {default: 10}},
		computed: {
			dataNames () {
				if (!this.data) return []
				return Object.keys(this.data)
			},
			dataNamesTruncated () {
				return this.dataNames.slice(0, this.limit)
			},
			maxQuantity () {
				return Object.values(this.data).sort((first, second) => second - first)[0]
			}
		},
		methods: {
			calculateBarHeight (quantity) {
				return 20 + ((180 * quantity) / this.maxQuantity)
			}
		}
	}
</script>

<style lang="scss">
    @import '../../scss/config';

    .histogram {
        display: flex;
        align-items: flex-end;
        justify-content: space-around;
        height: 240px;
        padding-bottom: 8px;
        .histogram-item {
            .quantity {
                transform: rotate(-90deg);
            }
            .bar {
                display: flex;
                padding: 4px;
                align-items: flex-end;
                background-color: rgba($info-colour, 0.2);
            }
        }
        .remainder {
            font-size: 14px;
            color: $info-colour;
        }
    }
</style>