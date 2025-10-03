/**
 * Navigation Section
 * Group of navigation items with optional heading
 */

import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface NavSectionProps {
  heading?: string
  children: ReactNode
  className?: string
}

export default function NavSection({
  heading,
  children,
  className,
}: NavSectionProps) {
  return (
    <div className={cn('space-y-1', className)}>
      {heading && (
        <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {heading}
        </h3>
      )}
      <div className="space-y-1">{children}</div>
    </div>
  )
}
