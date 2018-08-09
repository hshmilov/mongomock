<template>
    <div class="histogram">
        <div v-for="item, index in limitedData" class="histogram-item" @click="$emit('click-one', index)">
            <div class="item-bar">
                <img v-if="type === 'logo'" :src="`/src/assets/images/logos/${item.name}.png`" width="16">
                <div :style="{width: calculateBarHeight(item.value) + 'px'}">
                    <div class="bar growing-x" :title="item.name"></div>
                </div>
                <div class="quantity">{{item.value}}</div>
            </div>
            <div v-if="type ==='text'" class="item-title" :title="item.name">{{item.name}}</div>
        </div>
        <div v-if="data.length > limit" class="remainder">Top {{ limit }} of {{ data.length }}</div>
    </div>
</template>

<script>

	export default {
		name: 'x-histogram-chart',
		props: { data: { required: true }, limit: { default: 5 }, type: { default: 'text' } },
		computed: {
			limitedData () {
				return this.data.slice(0, this.limit)
			},
			maxQuantity () {
				let max = this.data[0].value
                this.data.slice(1).forEach((item) => {
                	if (item.value > max) {
                		max = item.value
					}
                })
				return max
			}
		},
		methods: {
			calculateBarHeight (quantity) {
				return ((240 * quantity) / this.maxQuantity)
			}
		}
	}
</script>

<style lang="scss">
    .histogram {
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        padding-bottom: 8px;
        position: relative;
        .histogram-item {
            width: 100%;
            cursor: pointer;
            .item-bar {
                display: flex;
                align-items: center;
                img {
                    margin-right: 8px;
                }
                .bar {
                    height: 20px;
                    background-color: rgba($grey-2, 0.4);
                    &:hover {
                        background-color: $grey-2;
                    }
                }
                .quantity {
                    margin-left: 8px;
                    flex: 1 0 auto;
                    text-align: right;
                    font-weight: 500;
                    font-size: 18px;
                }
            }
            .item-title {
                white-space: nowrap;
                text-overflow: ellipsis;
                overflow: hidden;
                width: 300px;
            }
        }
        .remainder {
            font-size: 12px;
            color: $grey-3;
            width: 100%;
            text-align: right;
        }
    }

</style>