/**
 * Dashboard Card
 * Reusable card component for dashboard sections
 */

import { ReactNode } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface DashboardCardProps {
  title: string
  description?: string
  children: ReactNode
  className?: string
  headerAction?: ReactNode
}

export default function DashboardCard({
  title,
  description,
  children,
  className,
  headerAction,
}: DashboardCardProps) {
  return (
    <Card className={cn('', className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle className="text-base font-semibold">{title}</CardTitle>
          {description && (
            <CardDescription className="text-sm">
              {description}
            </CardDescription>
          )}
        </div>
        {headerAction && <div className="flex items-center">{headerAction}</div>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}
