import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

// Tinted background + same-hue darker text — never grey text on a colored fill
// (Refactoring UI). A hairline inset ring keeps soft tints from floating.
const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold',
  {
    variants: {
      variant: {
        default: 'bg-zinc-100 text-zinc-700 ring-1 ring-inset ring-zinc-200/70',
        brand: 'bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-100',
        success: 'bg-gain-50 text-gain-700 ring-1 ring-inset ring-gain-100',
        danger: 'bg-loss-50 text-loss-700 ring-1 ring-inset ring-loss-100',
        warning: 'bg-warn-50 text-warn-800 ring-1 ring-inset ring-warn-200',
        outline: 'text-zinc-600 ring-1 ring-inset ring-zinc-300',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
