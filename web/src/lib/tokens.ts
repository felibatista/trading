// Runtime color tokens for canvas/SVG contexts (Recharts) that can't read Tailwind
// classes. Kept in sync with tailwind.config.js — the single source of design truth.
export const tokens = {
  brand: 'hsl(250 50% 50%)',
  brand400: 'hsl(248 56% 67%)',
  gain: 'hsl(155 62% 40%)',
  gain400: 'hsl(154 56% 48%)',
  loss: 'hsl(2 70% 54%)',
  warn: 'hsl(33 92% 48%)',
  grid: 'hsl(219 22% 90%)', // zinc-200
  axis: 'hsl(217 14% 64%)', // zinc-400
  ink: 'hsl(222 36% 11%)', // zinc-900
} as const
