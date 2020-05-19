<template>
  <svg
    width="24px"
    height="30px"
    viewBox="0 0 30 24"
    version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
  >
    <!-- Generator: Sketch 51.3 (57544) - http://www.bohemiancoding.com/sketch -->
    <template v-if="provider === 'thycotic'">
      <g
        stroke="#8DC73F"
        stroke-width="1"
        fill="none"
        fill-rule="evenodd"
      >
        <circle
          stroke-width="1.5"
          cx="12"
          cy="12"
          r="11.25"
        />
        <path
          d="M9.455,9.297 C9.455,9.297 10.286,7.019 12.047,7.219 C13.1449816,7.42567343 14.0362382,8.22707154 14.358,9.297"
          stroke-width="0.85"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <path
          d="M8.5,11 L15.5,11"
          stroke-width="1.85"
          stroke-linecap="round"
        />
        <path
          d="M8.5,13 L15.5,13"
          stroke-width="1.85"
          stroke-linecap="round"
        />
        <path
          d="M8.5,15 L15.5,15"
          stroke-width="1.85"
          stroke-linecap="round"
        />
      </g>
    </template>
    <template v-if="provider === 'cyberark'">
      <g
        fill-rule="nonzero"
        stroke="none"
        stroke-width="1"
        fill="none"
      >
        <polygon
          fill="#039BE5"
          points="3 7 12 2 12 7 7.5 9.5"
        />
        <polygon
          fill="#0277BD"
          points="12 17 16.369 14.551 16.369 14.549 21 12 21 17 12 22"
        />
        <polygon
          fill="#0277BD"
          points="12 7 12 2 21 7 16.5 9.5"
        />
        <polygon
          fill="#039BE5"
          points="3 16.5 7.5 14.5 12 17 12 22"
        />
        <polygon
          fill="#0277BD"
          points="3 7 7.5 9.5 7.5 14.5 3 16.5"
        />
        <polygon
          fill="#BDBDBD"
          points="12 12 12 7 16.5 9.5 16.5 14.5"
        />
        <polygon
          fill="#757575"
          points="7.5 9.5 12 7 12 12 7.5 14.5"
        />
      </g>
    </template>
    <template v-if="status === 'success'">
      <g
        stroke-width="1"
        fill="none"
        fill-rule="evenodd"
        transform="translate(-2, 0)"
        class="status success"
      >
        <circle
          fill="#FFFFFF"
          fill-rule="nonzero"
          cx="21"
          cy="19"
          r="4"
        />
        <path
          d="M21,24 C18.2385763,24 16,21.7614237 16,19 C16,16.2385763 18.2385763,14 21,14 C23.7614237,14 26,16.2385763 26,19 C26,21.7614237 23.7614237,24 21,24 Z M23.6775568,16.5891345 L20.2897728,20.0499554 L18.9474432,18.6786868 L18.2813484,19.3591418 L20.2897728,21.4108655 L24.3436516,17.2695895 L23.6775568,16.5891345 Z"
          fill="#0FBC18"
        />
      </g>
    </template>
    <template v-if="status === 'error'">
      <g
        stroke="none"
        stroke-width="1"
        fill="none"
        fill-rule="evenodd"
        class="status error"
      >
        <path
          d="M21.5,17 L21.5,24"
          stroke="#FFFFFF"
          stroke-width="2"
          stroke-linecap="square"
          fill-rule="nonzero"
        />
        <path
          d="M14,25 L21.5,13 L29,25 L14,25 Z M22.3333333,23.4 L22.3333333,21.8 L20.6666667,21.8 L20.6666667,23.4 L22.3333333,23.4 Z M22.3333333,20.2 L22.3333333,17 L20.6666667,17 L20.6666667,20.2 L22.3333333,20.2 Z"
          fill="#D0011B"
        />
      </g>
    </template>
  </svg>
</template>

<script>
export default {
  name: 'VaultLogo',
  props: {
    provider: {
      type: String,
      required: true,
    },
    status: {
      type: String,
      default: '',
    },
  },
};
</script>
