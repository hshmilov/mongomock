<template>
  <div
    class="cycle-wrapper"
    @mouseenter="inHover = true"
    @mouseleave="inHover = false"
  >

    <svg
      class="x-cycle"
    >
      <!-- Basis for the cycle - full circle, not coloured -->
      <circle
        class="pre"
        :r="radius"
        cx="50%"
        cy="50%"
      />

      <template v-for="(item, index) in data">
        <!-- Slice filled according to complete portion of current item -->
        <circle
          :key="index"
          :class="`slice extra-stroke-${(index % 6) + 1}`"
          :r="radius"
          cx="50%"
          cy="50%"
          :style="{
            strokeDasharray: `${sliceLength * Math.floor(item.status)} ${circleLength}`,
            strokeDashoffset: -(index * sliceLength)
          }"
        >
        </circle>
        <!-- Marker of 1px in the start of the slice -->
        <circle
          :key="index+'_marker'"
          class="marker"
          :r="radius"
          cx="50%"
          cy="50%"
          :style="{
            strokeDasharray: `4 ${circleLength}`,
            strokeDashoffset: -(index * sliceLength)
          }"
        />
      </template>

      <template v-if="status < 100">
        <!-- Percentage of completion of the cycle, updating while cycle proceeds -->
        <text
          v-if="currentStageName"
          x="50%"
          y="50%"
          text-anchor="middle"
          class="subtitle"
        >{{ currentStageName }}...
        </text>
      </template>

      <template v-else>
        <!-- Cycle is complete, namely status is stable -->
        <text
          x="50%"
          y="50%"
          text-anchor="middle"
          class="cycle-title"
        >STABLE</text>
        <path
          d="M160 100 L140 130 L130 120"
          stroke-width="4"
          class="check"
        />
      </template>
    </svg>
    <x-tooltip
      v-if="showTooltip"
      ref="tooltip"
    >
      <template slot="body">
        <div class="tooltip-content">
          <x-table
            :data="currentStageAdditionalData"
            :fields="additionalDataFields"
            id-field="key"
          />
        </div>
      </template>
    </x-tooltip>
  </div>
</template>

<script>
  import xTable from '../../axons/tables/Table.vue'
  import xTooltip from '../../axons/popover/Tooltip.vue'

  import {pluginMeta} from '../../../constants/plugin_meta'
  import _sortBy from 'lodash/sortBy'

  const statuses = {
    'Pending': {
        key: 2,
        label: 'Not Started'
    },
    'Fetching': {
      key: 1,
      label: 'Fetching...'
    },
    'Done': {
      key: 3,
      label: 'Done'
    }
  }

  export default {
    name: 'XCycle',
    components: {xTooltip, xTable},
    component: {
      xTable
    },
    props: {
      data: {
        required: true
      },
      radius: {
        default: 80
      }
    },
    data () {
      return {
        inHover: false,
        additionalDataFields: [{
          name: 'adapters',
          title: 'Pending\nAdapters',
          type: 'array',
          format: 'discrete',
          items: {
            type: 'string',
            format: 'logo',
            enum: []
          },
          sort: true,
          unique: true
        },
          {name: 'name', path: ['name'], title: 'Name', type: 'string'},
          {name: 'statusLabel', path: ['statusLabel'], title: 'Status', type: 'string'},
        ]
      }
    },
    computed: {
      circleLength() {
        return (2 * Math.PI * this.radius)
      },
      sliceCount() {
        if (!this.data) return 0
        return this.data.length
      },
      sliceLength() {
        if (!this.circleLength || !this.sliceCount) return 0
        return this.circleLength / this.sliceCount
      },
      status() {
        if (!this.data || !this.data.length) return 100
        return this.data.reduce((sum, item) => sum + item.status, 0) * 100 / this.sliceCount
      },
      currentStage() {
        if (!this.data || !this.data.length) return null
        let stage = this.data[0]
        let i = 1
        while (i < this.data.length && stage.status === 1) {
          stage = this.data[i]
          i++
        }
        return {...stage, index: i}
      },
      currentStageName() {
        if (!this.currentStage) return ''
        return this.currentStage.name.split('_').join(' ')
      },
      currentStageAdditionalData() {
        const additionalData = this.currentStage.additional_data || []
        const temp = Object.keys(additionalData).reduce((acc, current, index) => {
          const name = current.split('_').slice(0,-1).join('_')
          const title = pluginMeta[name] ? pluginMeta[name].title : name.split('_').join(' ')
          if(this.currentStage.additional_data[current] !== 'Done') {
            if(!acc.find((item) => item.name === title && item.status === 'Fetching'))
              acc.push({
                key:index,
                adapters: [current.slice(0, -2)] ,
                name: title,
                status: this.currentStage.additional_data[current],
                statusLabel: statuses[this.currentStage.additional_data[current]].label
              })
            }
          return acc
        }, [])
        return _sortBy(temp, [function(obj){ return statuses[obj.status].key}, function(obj){ return obj.name }])
      },
      showTooltip() {
        return this.inHover && this.currentStageAdditionalData.length > 0
      }
    }
  }
</script>

<style lang="scss">

  .cycle-wrapper {
    flex: 1 0 auto;
    display: flex;
    position: relative;

    .x-tooltip {
      max-width: none;
      position: absolute;
      top: 51%;
      right:0;
      z-index: 1000;
      bottom: auto;
    }

    .x-table {
      max-height: 210px;
      .table {
        thead {
          th {
            box-shadow: none;
            white-space: pre;
            line-height: 18px;
            vertical-align: bottom;
            min-width: auto;
            padding-bottom: 5px;
          }
        }
      }
    }
  }

  .x-cycle {
    margin: auto;
    height: 175px;
    position: relative;

    circle {
      fill: none;
      stroke-width: 12;

      &.pre {
        stroke: $grey-1;
      }

      &.marker {
        stroke: $theme-white;
        stroke-width: 16;
      }

      &.post {
        stroke-width: 0;
        fill: $theme-white;
      }

      &.slice, &.marker {
        transform-origin: 50% 50%;
        transform: rotate(-90deg);
      }
    }

    text {
      stroke: none;
      font-size: 10px;

            &.cycle-title {
                fill: $grey-5;
                font-size: 24px;
            }

      &.subtitle {
        font-size: 18px;
      }
    }

    path {
      fill: none;
      stroke: none;

      &.check {
        stroke: $indicator-success;
        stroke-dasharray: 60;
        stroke-dashoffset: -60;
        animation: check-stroke ease-in-out .8s forwards;
      }
    }
  }

  @keyframes check-stroke {
    100% {
      stroke-dashoffset: 0;
    }
  }

</style>