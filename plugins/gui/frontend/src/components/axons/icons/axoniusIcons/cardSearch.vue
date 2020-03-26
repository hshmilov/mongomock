<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="17"
    height="16"
    viewBox="0 0 17 16"
  >
    <path
      fill="none"
      fill-rule="evenodd"
      stroke="#979797"
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M16 16l-5-5 5 5zm-4-9.5C12 9.538 9.538 12 6.5 12S1 9.538 1 6.5 3.462 1 6.5 1 12 3.462 12 6.5z"
    />
  </svg>
</template>

<script>
export default {
  name: 'CardSearch',
  props: {
    color: {
      type: String,
      default: '#FF7E46',
    },
  },
};
</script>
