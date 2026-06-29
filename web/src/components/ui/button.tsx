import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

// Action hierarchy (Refactoring UI: semantics are secondary to hierarchy):
// one loud primary, quieter secondary/outline/ghost, and a *quiet* destructive
// for non-primary destructive actions — the loud `destructive` is reserved for
// the confirmation step where stopping is genuinely the primary action.
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-[background-color,box-shadow,transform] duration-150 disabled:pointer-events-none disabled:opacity-50 active:translate-y-px',
  {
    variants: {
      variant: {
        default:
          'bg-brand-600 text-white shadow-sm hover:bg-brand-500 active:bg-brand-700',
        secondary: 'bg-zinc-100 text-zinc-800 hover:bg-zinc-200 active:bg-zinc-200',
        outline:
          'bg-white text-zinc-700 shadow-xs ring-1 ring-inset ring-zinc-300 hover:bg-zinc-50 hover:text-zinc-900',
        ghost: 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900',
        destructive: 'bg-loss-600 text-white shadow-sm hover:bg-loss-500 active:bg-loss-700',
        destructiveQuiet:
          'bg-white text-loss-700 shadow-xs ring-1 ring-inset ring-loss-200 hover:bg-loss-50 hover:ring-loss-300',
        link: 'text-brand-700 underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-10 px-5',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
)
Button.displayName = 'Button'
