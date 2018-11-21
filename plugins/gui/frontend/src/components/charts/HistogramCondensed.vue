<template>
    <div class="x-histogram-cond" :class="{disabled: readOnly}">
        <div v-for="item, index in limitedData" class="item-bar" @click="$emit('click-one', index)">
            <img :src="require(`Logos/${item.name}.png`)" width="30">
            <div>
                <div :style="{width: calculateBarHeight(item.value) + 'px'}">
                    <div class="bar growing-x" :title="item.name"></div>
                </div>
                <div class="quantity">{{ item.title || item.value }}</div>
            </div>
        </div>
        <div v-if="data.length > limit" class="remainder">Top {{ limit }} of {{ data.length }}</div>
    </div>
</template>

<script>

    export default {
        name: 'x-histogram-condensed',
        props: {
            data: { required: true }, limit: { default: 12 }, readOnly: { default: false }
        },
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
                return ((280 * quantity) / this.maxQuantity)
            }
        }
    }
</script>

<style lang="scss">
    .x-histogram-cond {
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        padding-bottom: 8px;
        position: relative;
        .item-bar {
            width: 100%;
            cursor: pointer;
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            img {
                margin-right: 8px;
            }
            .bar {
                height: 8px;
                background-color: rgba($grey-2, 0.8);
                &:hover {
                    background-color: $grey-2;
                }
            }
            .quantity {
                font-weight: 400;
                font-size: 16px;
                text-align: left;
                margin-top: 2px;
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
                    background-color: rgba($grey-2, 0.8);
                }
            }
        }
    }

</style>