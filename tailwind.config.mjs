export default {
  content: ["./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}"],
  theme: {
    extend: {
      colors: {
        /* RAL 1035 Pearl Beige palette — replaces sky-* across the site */
        sky: {
          50:  "#FAF7F4",
          100: "#F0EAE3",
          200: "#E2D8CC",
          300: "#C9BAA8",
          400: "#A89580",
          500: "#8B7A66",
          600: "#6A5D4D",
          700: "#574C3E",
          800: "#453D32",
          900: "#352F26",
          950: "#1E1A15",
        },
        slate: {
          50: "#F8F6F3",
        },
      },
    },
  },
};
