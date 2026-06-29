/** @type {import('tailwindcss').Config} */
// Token system distilled from "Refactoring UI": shades defined up front (HSL),
// greys tinted cool, saturation boosted at the ends, a two-part elevation scale,
// and a brand hue kept distinct from the semantic gain/loss colors.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        // Neutrals: cool blue-tinted slate (greys don't have to be grey).
        zinc: {
          50: 'hsl(220 33% 98%)',
          100: 'hsl(220 26% 95%)',
          200: 'hsl(219 22% 90%)',
          300: 'hsl(218 18% 82%)',
          400: 'hsl(217 14% 64%)',
          500: 'hsl(218 13% 49%)',
          600: 'hsl(219 16% 39%)',
          700: 'hsl(220 21% 29%)',
          800: 'hsl(221 28% 18%)',
          900: 'hsl(222 36% 11%)',
        },
        // Brand: calm indigo "intelligence" — kept apart from gain/loss.
        brand: {
          50: 'hsl(247 70% 97%)',
          100: 'hsl(246 68% 93%)',
          200: 'hsl(246 64% 87%)',
          300: 'hsl(247 60% 78%)',
          400: 'hsl(248 56% 67%)',
          500: 'hsl(249 54% 58%)',
          600: 'hsl(250 50% 50%)',
          700: 'hsl(251 48% 42%)',
          800: 'hsl(251 44% 34%)',
          900: 'hsl(252 40% 26%)',
        },
        // Positive / money up.
        gain: {
          50: 'hsl(150 65% 96%)',
          100: 'hsl(151 58% 89%)',
          200: 'hsl(152 54% 78%)',
          300: 'hsl(153 52% 62%)',
          400: 'hsl(154 56% 48%)',
          500: 'hsl(155 62% 40%)',
          600: 'hsl(157 66% 33%)',
          700: 'hsl(159 64% 26%)',
          800: 'hsl(160 58% 20%)',
          900: 'hsl(162 52% 15%)',
        },
        // Negative / money down.
        loss: {
          50: 'hsl(7 85% 97%)',
          100: 'hsl(7 80% 93%)',
          200: 'hsl(6 78% 86%)',
          300: 'hsl(5 76% 76%)',
          400: 'hsl(4 74% 64%)',
          500: 'hsl(2 70% 54%)',
          600: 'hsl(359 64% 47%)',
          700: 'hsl(356 60% 40%)',
          800: 'hsl(354 56% 32%)',
          900: 'hsl(352 50% 24%)',
        },
        // Warnings (paper mode, cautions).
        warn: {
          50: 'hsl(45 100% 96%)',
          100: 'hsl(44 96% 88%)',
          200: 'hsl(43 95% 76%)',
          300: 'hsl(40 94% 64%)',
          400: 'hsl(37 92% 53%)',
          500: 'hsl(33 92% 48%)',
          600: 'hsl(28 90% 43%)',
          700: 'hsl(24 84% 36%)',
          800: 'hsl(22 78% 30%)',
          900: 'hsl(20 72% 24%)',
        },
      },
      boxShadow: {
        // Two-part, cool-tinted elevation scale. The tight ambient part fades
        // out as elevation rises.
        xs: '0 1px 2px 0 hsl(222 40% 20% / 0.05)',
        sm: '0 1px 2px 0 hsl(222 40% 20% / 0.06), 0 1px 1px -0.5px hsl(222 40% 22% / 0.08)',
        DEFAULT: '0 4px 10px -3px hsl(222 40% 25% / 0.10), 0 2px 4px -2px hsl(222 40% 25% / 0.06)',
        md: '0 4px 10px -3px hsl(222 40% 25% / 0.10), 0 2px 4px -2px hsl(222 40% 25% / 0.06)',
        lg: '0 14px 24px -10px hsl(222 42% 25% / 0.15), 0 6px 10px -6px hsl(222 40% 25% / 0.08)',
        xl: '0 28px 48px -16px hsl(222 45% 22% / 0.22)',
      },
      keyframes: {
        'pulse-live': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.45', transform: 'scale(0.85)' },
        },
        'rise-in': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'pulse-live': 'pulse-live 2s ease-in-out infinite',
        'rise-in': 'rise-in 0.4s ease-out both',
      },
    },
  },
  plugins: [],
}
