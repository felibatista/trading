import * as React from 'react'
import { cn } from '@/lib/utils'

// Panels lean on a two-part shadow + hairline ring instead of a hard border
// (Refactoring UI: use fewer borders), and read as raised off the cool canvas.
export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-xl bg-white shadow-md ring-1 ring-zinc-900/[0.04] transition-shadow duration-200',
        className,
      )}
      {...props}
    />
  ),
)
Card.displayName = 'Card'

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col gap-1 p-5', className)} {...props} />
  ),
)
CardHeader.displayName = 'CardHeader'

// A small, quiet uppercase eyebrow — the label that supports the data, not steals from it.
export const CardEyebrow = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('text-[11px] font-semibold uppercase tracking-wider text-zinc-500', className)}
      {...props}
    />
  ),
)
CardEyebrow.displayName = 'CardEyebrow'

export const CardTitle = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('font-display text-sm font-semibold tracking-tight text-zinc-800', className)}
      {...props}
    />
  ),
)
CardTitle.displayName = 'CardTitle'

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-5 pt-0', className)} {...props} />
  ),
)
CardContent.displayName = 'CardContent'
