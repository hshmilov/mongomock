<template>
  <svg
    width="14px"
    height="16px"
    viewBox="0 0 14 16"
    version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <g
      id="Dashboard"
      stroke="none"
      stroke-width="1"
      fill="none"
      fill-rule="evenodd"
    >
      <g
        id="Group-13"
        transform="translate(-1186.000000, -592.000000)"
      >
        <g transform="translate(1186.000000, 592.000000)">
          <rect
            id="Rectangle-Copy-3"
            :fill="leftFill"
            :stroke="leftStroke"
            x="7"
            y="0"
            width="7"
            height="16"
          />
          <rect
            id="Rectangle-Copy-4"
            :fill="rightFill"
            :stroke="rightStroke"
            stroke-width="0.4"
            x="0.2"
            y="0.2"
            width="6.6"
            height="15.6"
          />
        </g>
      </g>
    </g>
  </svg>
</template>

<script>
export default {
  name: 'Toggle',
  props: {
    leftFill: {
      type: String,
      default: 'Transparent',
    },
    leftStroke: {
      type: String,
      default: '#DEDEDE',
    },
    rightFill: {
      type: String,
      default: '#DEDEDE',
    },
    rightStroke: {
      type: String,
      default: '#DEDEDE',
    },
  },
};
</script>
