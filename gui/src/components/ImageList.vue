<template>
    <div class="image-list d-flex" v-bind:class="{'flex-row': !vertical,
	    'flex-column align-content-start justify-content-around': vertical }">
        <div v-for="image in limitedData" v-bind:class="{ 'd-flex flex-row': names !== undefined}">
            <img :src="`/src/assets/images/logos/${image}.png`"
                 class="img-md image-list-item" :title="names? names[image] : image.split('_')[0]">
            <div v-if="names">{{ names[image] }}</div>
        </div>
        <span v-if="data.length > limit" class="image-list-total">(out of {{ data.length }})</span>
    </div>
</template>

<script>
    export default {
        name: 'image-list',
        props: ['data', 'limit', 'vertical', 'names'],
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

    .image-list {
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
        .image-list-total {
            font-size: 80%;
            text-transform: uppercase;
        }
    }
</style>