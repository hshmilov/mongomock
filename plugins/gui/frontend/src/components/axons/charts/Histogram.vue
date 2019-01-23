<template>
    <div class="x-histogram" :class="{disabled: readOnly, condensed}">
        <div v-for="item, index in limitedData" class="histogram-item" @click="$emit('click-one', index)">
            <div class="item-bar">
                <img v-if="condensed" :src="require(`Logos/${item.name}.png`)" width="30">
                <div class="bar-container">
                    <div :style="{width: calculateBarHeight(item.value) + 'px'}">
                        <div class="bar growing-x" :title="item.name"></div>
                    </div>
                    <div class="quantity">{{ item.title || item.value }}</div>
                </div>
            </div>
            <div v-if="!condensed" class="item-title" :title="item.name">{{item.name}}</div>
        </div>
        <div v-if="data.length > limit" class="remainder">Top {{ limit }} of {{ data.length }}</div>
    </div>
</template>

<script>
    export default {
        name: 'x-histogram',
        props: {
            data: {required: true},
            limit: {default: 5},
            condensed: {default: false},
            readOnly: {default: false}
        },
        computed: {
            maxWidth() {
                if (this.condensed) return 280
                return 240
            },
            limitedData() {
                return this.data.slice(0, this.limit)
            },
            maxQuantity() {
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
            calculateBarHeight(quantity) {
                return ((this.maxWidth * quantity) / this.maxQuantity)
            }
        }
    }
</script>

<style lang="scss">
    .x-histogram {
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        padding-bottom: 8px;
        position: relative;

        .histogram-item {
            width: 100%;
            cursor: pointer;

            .bar-container {
                display: flex;
                width: 100%;
            }

            .item-bar {
                display: flex;
                align-items: center;
                line-height: 24px;

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
                    font-weight: 400;
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

        &.disabled {
            .histogram-item {
                cursor: default;

                .bar:hover {
                    background-color: rgba($grey-2, 0.4);
                }
            }
        }

        &.condensed {
            .bar-container {
                width: calc(100% - 36px);
                flex-direction: column;
            }

            .item-bar {
                width: 100%;
                cursor: pointer;
                margin-bottom: 12px;

                .bar {
                    height: 8px;
                    background-color: rgba($grey-2, 0.8);
                }

                .quantity {
                    font-size: 16px;
                    text-align: left;
                    margin-top: 2px;
                    margin-left: 0;
                }
            }

            &.disabled .histogram-item .bar:hover {
                background-color: rgba($grey-2, 0.8);
            }
        }
    }

</style>