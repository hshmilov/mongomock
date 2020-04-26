<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="152.168"
    height="147.319"
    viewBox="0 0 152.168 147.319"
  >
    <g transform="translate(1.942 17.316)">
      <g transform="translate(-895 -511)">
        <g transform="translate(897 496.5)">
          <g transform="translate(7 18.5)">
            <path
              fill="none"
              :stroke="color"
              stroke-width="8"
              d="M118.712 2.946a71.54 71.54 0 0 1 0 100.286 69.417 69.417 0 0 1-99.042 0C-7.681 75.537-4.965 28.277 22.386.582"
            />
          </g>
          <g transform="rotate(-48 20.969 9.264)">
            <path
              fill="none"
              :stroke="color"
              stroke-width="8"
              d="M0 0l23.508 23.476m0 0L0 46.952"
            />
          </g>
          <g transform="translate(51 35.5)">
            <path
              :fill="color"
              :stroke="color"
              d="M43.083 68H3.917A3.906 3.906 0 0 1 0 64.108V32.97a3.906 3.906 0 0 1 3.917-3.892h39.166A3.906 3.906 0 0 1 47 32.97v31.138A3.906 3.906 0 0 1 43.083 68z"
            />
            <path
              fill="none"
              :stroke="color"
              stroke-width="8"
              d="M23.841 0A15.619 15.619 0 0 0 8.174 15.569v15.569h31.333V15.569A15.619 15.619 0 0 0 23.841 0z"
            />
          </g>
        </g>
      </g>
    </g>
  </svg>
</template>

<script>
export default {
  name: 'ResetPassword',
  props: {
    color: {
      type: String,
      default: '#FFFFFF',
    },
  },
};
</script>
