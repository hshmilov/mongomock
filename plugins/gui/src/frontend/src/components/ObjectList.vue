<template>
    <div class="object-list d-flex" v-bind:class="{'flex-row': !vertical,
	    'flex-column align-content-start justify-content-around': vertical }">
        <div v-for="item, index in limitedData" :key="index" class="d-flex"
             v-bind:class="{ 'flex-row': names !== undefined, 'flex-item': !names }">
            <template v-if="type === 'image-list'">
                <img :src="`/src/assets/images/logos/${item}.png`"
                     :class="`${vertical? 'img-lg' : 'img-md'} image-list-item`">
            </template>
            <template v-else-if="type === 'tag-list'"><div class="tag-item">{{item}}</div></template>
            <template v-else><span>{{(index? ', ': '') + item}}</span></template>
            <div v-if="names">{{ names[item] }}</div>
        </div>
        <div v-if="data.length > limit" class="list-total">({{ data.length - limit }} more)</div>
    </div>
</template>

<script>
    export default {
        name: 'object-list',
        props: ['type', 'data', 'limit', 'vertical', 'names'],
        computed: {
            limitedData() {
                if (this.data.length <= this.limit) {
                    return this.data
                }
                return this.data.slice(0, this.limit)
            }
        }
    }
</script>

<style lang="scss">
    @import '../scss/config';

    .object-list {
        display: inline-block;
        vertical-align: middle;
        line-height: 24px;
        flex-wrap: wrap;
        .d-flex.flex-row {
            vertical-align: middle;
            line-height: 36px;
        }
        .tag-item {
            flex: 0 1 auto;
        }
        .flex-item {
            flex: 0 0 auto;
        }
        .image-list-item {
            margin-right: 8px;
        }
        &.flex-column {
            .flex-row {
                padding: 8px 0;
            }
        }
        .list-total {
            font-size: 80%;
            text-transform: uppercase;
        }
    }
</style>