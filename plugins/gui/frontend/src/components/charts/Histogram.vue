<template>
    <div class="histogram">
        <div v-for="name in dataNamesTruncated" class="histogram-item" @click="$emit('click-bar', name)">
            <div class="quantity">{{data[name]}}</div>
            <div :style="{height: calculateBarHeight(data[name]) + 'px'}">
                <div class="bar" :title="name">
                    <img :src="`/src/assets/images/logos/${name}.png`" width="16">
                </div>
            </div>
        </div>
        <div v-if="dataNames.length > limit" class="remainder">+{{dataNames.length - limit}}</div>
    </div>
</template>

<script>

	export default {
		name: 'x-histogram-chart',
		props: {data: {required: true}, limit: {default: 10}},
		computed: {
			dataNames () {
				if (!this.data) return []
				return Object.keys(this.data).sort((first, second) => this.data[second] - this.data[first])
			},
			dataNamesTruncated () {
				return this.dataNames.slice(0, this.limit)
			},
			maxQuantity () {
				return this.data[this.dataNames[0]]
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
    .histogram {
        display: flex;
        align-items: flex-end;
        justify-content: space-around;
        padding-bottom: 8px;
        .histogram-item {
            .quantity {
                transform: rotate(-90deg);
            }
            .bar {
                animation: rise 1s;
                height: 100%;
                overflow: hidden;
                display: flex;
                padding: 4px;
                align-items: flex-end;
                background-color: rgba($indicator-blue, 0.2);
                &:hover {
                    box-shadow: 2px 2px 12px -2px $theme-gray-dark;
                    cursor: pointer;
                }
            }
        }
        .remainder {
            font-size: 14px;
            color: $indicator-blue;
        }
    }
    @keyframes rise {
        from {
            height: 0;
        }
        to {
            height: 100%;
        }
    }

</style>