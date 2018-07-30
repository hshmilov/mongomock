<template>
    <div class="x-summary-chart" :class="{updating: enumerating}">
        <template v-for="item in displayData">
            <div class="summary" :class="{highlight: item.highlight}">{{ item.value }}</div>
            <div class="title">{{ item.name }}</div>
        </template>
    </div>
</template>

<script>
	export default {
		name: 'x-summary-chart',
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
                    let jumpValue = Math.max(10, Math.ceil(this.data[index].value / 200))
                    if (item.value === this.data[index].value) return item
                    this.enumerating = true
                    if (this.data[index].value > item.value) {
                        return { ...item, value: Math.min(item.value + jumpValue,  this.data[index].value)}
                    }
                    // Smaller - need to subtract
					return { ...item, value: Math.max(item.value - jumpValue,  this.data[index].value)}
                })
            }, 10)
        }
	}
</script>

<style lang="scss">
    .x-summary-chart {
        display: grid;
        grid-template-columns: 1fr 2fr;
        .summary {
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