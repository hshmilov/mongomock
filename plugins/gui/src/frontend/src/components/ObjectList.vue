<template>
    <div class="object-list d-flex" v-bind:class="{'flex-row': !vertical,
	    'flex-column align-content-start justify-content-around': vertical }">
        <div v-for="item, index in limitedData" :key="item" v-bind:class="{ 'd-flex flex-row': names !== undefined}">
            <template v-if="type === 'image-list'">
                <img :src="`/src/assets/images/logos/${item}.png`"
                     class="img-md image-list-item" :title="names? names[item] : item.split('_')[0]">
            </template>
            <template v-else-if="type === 'tag-list'"><span class="tag-item">{{item}}</span></template>
            <template v-else><span>{{(index? ',': '') + item}}</span></template>
            <div v-if="names && names.length">{{ names[item] }}</div>
        </div>
        <span v-if="data.length > limit" class="list-total">({{ data.length - limit }} more)</span>
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
        .image-list-item {
            width: 24px;
            height: 24px;
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