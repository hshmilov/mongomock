<template>
    <div class="x-paginator">
        <x-button
            v-if="this.numOfItems > this.limit"
            link
            :disabled="isBackDisabled"
            @click="onClickPage(1)"
            @keyup.enter="onClickPage(1)">
                &lt;&lt;
        </x-button>
        <x-button
            v-if="this.numOfItems > this.limit"
            link
            :disabled="isBackDisabled"
            @click="onClickPage(page-1)"
            @keyup.enter="onClickPage(page-1)">
                &lt;
        </x-button>
        <div class="pagintator-text" >
            Top
            <template v-if="page === 1">
               <strong> {{ to }}</strong>
            </template>
            <template v-else>
                <strong> {{ from }} </strong>
                    - <strong> {{ to }}</strong>
            </template>
            of <strong> {{ numOfItems }}</strong>
        </div>
        <x-button
            v-if="this.numOfItems > this.limit"
            link
            :disabled="isNextDisabled"
            @click="onClickPage(page+1)"
            @keyup.enter="onClickPage(page+1)">
                &gt;
        </x-button>
        <x-button
            v-if="this.numOfItems > this.limit"
            link
            :disabled="isNextDisabled"
            @click="onClickPage(pageCount)"
            @keyup.enter="onClickPage(pageCount)">
                    &gt;&gt;
        </x-button>
    </div>
</template>
<script>
import xButton from '../../axons/inputs/Button.vue'

export default {
    name: "x-paginator",
    components: { xButton },
    data() {
        return {
            from: 1,
            page: 1,
        };
    },
    props: {
        limit: {
            type: Number,
            default: 5
        },
        value: {
            type: Array,
            required: true
        },
        data:  {
            type: Array,
            required: true
        }
    },
    computed: {
        to() {
            if(this.limit > this.numOfItems) {
                return this.numOfItems
            }
            return Math.min(this.page * this.limit, this.numOfItems)
        },
        numOfItems() {
            return this.data.length
        },
        pageCount() {
            return this.numOfItems % this.limit === 0 ?
                            Math.floor(this.numOfItems / this.limit) :
                            Math.floor(this.numOfItems / this.limit) + 1
        },
        isNextDisabled() {
            return !(this.page + 1 <= this.pageCount && this.to < this.numOfItems)
        },
        isBackDisabled() {
            return !(this.page - 1 >= 1);
        }
    },
    watch: {
        to(val , oldVal) {
            if( val !== oldVal) {
                this.$emit('input', this.data.slice(this.from - 1, this.to))
            }
        },
        data() {
            this.$emit('input', this.data.slice(this.from - 1, this.to))
        }
    },
    methods: {
        onClickPage(page) {
            this.page = page;
            if( this.page < 0 || this.page > this.pageCount) {
                return
            }
            this.from = this.to - this.limit + 1;
            if( this.numOfItems % this.limit !== 0 && this.page === this.pageCount) {
                this.from = this.numOfItems - this.numOfItems % this.limit + 1
            }
            this.$emit('input', this.data.slice(this.from - 1, this.to))
        }
    },
    created() {
        this.$emit('input', this.data.slice(0, this.limit))
    }
}
</script>
<style lang="scss">
  .x-paginator {
    display: flex;
    min-width: 200px;
    margin: auto;
    min-height: 28px;
    align-items: center;
    background: $theme-white;
    border-bottom: 2px solid $theme-white;
    border-radius: 2px;
    .pagintator-text {
        margin: auto;
    }

    .x-button{
        width: 15px;
        background: transparent;
        display: flex;
        justify-content: center;
        color: black;
        &:hover:not(.disabled) {
            color: black;
            box-shadow: 1px 1px 3px grey;
        }
    }
    .active:hover {
      cursor: default;
    }

  }


</style>