<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="4"
    height="16"
    viewBox="0 0 4 16"
  >
    <g
      fill="none"
      fill-rule="evenodd"
      stroke="#979797"
    >
      <circle
        cx="2"
        cy="2"
        r="1.5"
      />
      <circle
        cx="2"
        cy="8"
        r="1.5"
      />
      <circle
        cx="2"
        cy="14"
        r="1.5"
      />
    </g>
  </svg>
</template>

<script>
export default {
  name: 'VerticalDots',
  props: {
    color: {
      type: String,
      default: '#FF7E46',
    },
  },
};
</script>
