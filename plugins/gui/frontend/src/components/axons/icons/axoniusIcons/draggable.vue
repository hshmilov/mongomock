<template>
  <svg
    width="11px"
    height="20px"
    viewBox="0 0 11 20"
    version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <g
      id="Symbols"
      stroke="none"
      stroke-width="1"
      fill="none"
      fill-rule="evenodd"
    >
      <g
        id="Query-Wizard-Full"
        transform="translate(-13.000000, -524.000000)"
        :fill="color"
      >
        <g
          id="Group-2"
          transform="translate(13.000000, 524.000000)"
        >
          <circle
            id="Oval"
            cx="9"
            cy="2"
            r="2"
          />
          <circle
            id="Oval-Copy-2"
            cx="9"
            cy="10"
            r="2"
          />
          <circle
            id="Oval-Copy-4"
            cx="9"
            cy="18"
            r="2"
          />
          <circle
            id="Oval-Copy"
            cx="2"
            cy="2"
            r="2"
          />
          <circle
            id="Oval-Copy-3"
            cx="2"
            cy="10"
            r="2"
          />
          <circle
            id="Oval-Copy-5"
            cx="2"
            cy="18"
            r="2"
          />
        </g>
      </g>
    </g>
  </svg>
</template>

<script>
export default {
  name: 'Draggable',
  props: {
    color: {
      type: String,
      default: '#FF7E46',
    },
  },
};
</script>
