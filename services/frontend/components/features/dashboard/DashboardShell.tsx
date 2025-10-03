/**
 * Dashboard Shell
 * Container component for dashboard pages with heading and description
 */

import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface DashboardShellProps {
  heading: string
  description?: string
  children: ReactNode
  className?: string
}

export default function DashboardShell({
  heading,
  description,
  children,
  className,
}: DashboardShellProps) {
  return (
    <div className={cn('flex flex-col gap-6', className)}>
      {/* Header */}
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">{heading}</h1>
        {description && (
          <p className="text-muted-foreground">{description}</p>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col gap-6">{children}</div>
    </div>
  )
}
