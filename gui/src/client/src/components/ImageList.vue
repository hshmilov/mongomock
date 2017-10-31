<template>
    <span>
        <img v-for="image in limitedData" :src="`/src/assets/images/logos/${image}.png`"
             class="img-md" :title="image.split('_').join(' ')">
        <span v-if="data.length > limit">({{ data.length }})</span>
    </span>
</template>

<script>
    export default {
        name: 'image-list',
        props: ['data', 'limit'],
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

</style>