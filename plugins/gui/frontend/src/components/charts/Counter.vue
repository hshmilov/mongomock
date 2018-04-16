<template>
    <div class="x-grid x-grid-col-2 counter" :class="{updating: enumerating}">
        <template v-for="item in displayData">
            <div class="count" :class="{highlight: item.highlight}">{{ item.count }}</div>
            <div class="title">{{ item.title }}</div>
        </template>
    </div>
</template>

<script>
	export default {
		name: 'x-counter-chart',
        props: { data: {required: true}},
        data() {
			return {
			    displayData: [ ...this.data ],
                enumerating: false
            }
        },
        watch: {
			data() {
                this.enumerating = true
            }
        },
        updated() {
			if (!this.enumerating) return
            setTimeout(() => {
                this.enumerating = false
                this.displayData = this.displayData.map((item, index) => {
                    let jumpValue = Math.max(10, Math.ceil(this.data[index].count / 200))
                    if (item.count === this.data[index].count) return item
                    this.enumerating = true
                    if (this.data[index].count > item.count) {
                        return { ...item, count: Math.min(item.count + jumpValue,  this.data[index].count)}
                    }
                    // Smaller - need to subtract
					return { ...item, count: Math.max(item.count - jumpValue,  this.data[index].count)}
                })
            }, 10)
        }
	}
</script>

<style lang="scss">
    .counter {
        .count {
            font-size: 60px;
            display: inline;
            color: $theme-blue;
            &.highlight {
                color: $theme-orange;
            }
        }
        .title {
            display: inline-block;
            max-width: 160px;
            text-align: left;
            margin: auto;
            margin-left: 12px;
        }
    }
</style>