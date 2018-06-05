<template>
    <div class="histogram">
        <div v-for="item, index in limitedData" class="histogram-item" @click="$emit('click-one', index)">
            <div class="item-bar">
                <img v-if="type === 'logo'" :src="`/src/assets/images/logos/${item.name}.png`" width="16">
                <div :style="{width: calculateBarHeight(item.count) + 'px'}">
                    <div class="bar growing-x" :title="item.name"></div>
                </div>
                <div class="quantity">{{item.count}}</div>
            </div>
            <div v-if="type ==='text'" class="item-title" :title="item.name">{{item.name}}</div>
        </div>
        <div v-if="processedData.length > limit" class="remainder">+{{processedData.length - limit}}</div>
    </div>
</template>

<script>

	export default {
		name: 'x-histogram-chart',
		props: {data: {required: true}, limit: {default: 6}, sort: {default: false}, type: {default: 'text'}},
		computed: {
			processedData () {
				if (!this.data) return []
                if (!this.sort) return this.data
				return this.data.sort((first, second) => second.count - first.count)
			},
			limitedData () {
				return this.processedData.slice(0, this.limit)
			},
			maxQuantity () {
				let max = this.processedData[0].count
                this.processedData.slice(1).forEach((item) => {
                	if (item.count > max) {
                		max = item.count
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
            margin-bottom: 12px;
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
            position: absolute;
            bottom: 0;
            font-size: 14px;
            color: $indicator-info;
        }
    }

</style>