/**
 * Navigation Item
 * Individual navigation link with icon and active state
 */

'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItemProps {
  href: string
  label: string
  icon?: LucideIcon
  badge?: string | number
  className?: string
}

export default function NavItem({
  href,
  label,
  icon: Icon,
  badge,
  className,
}: NavItemProps) {
  const pathname = usePathname()
  const isActive = pathname === href || pathname.startsWith(`${href}/`)

  return (
    <Link
      href={href}
      className={cn(
        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
        isActive
          ? 'bg-accent text-accent-foreground'
          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
        className
      )}
    >
      {Icon && <Icon className="h-4 w-4" />}
      <span className="flex-1">{label}</span>
      {badge !== undefined && (
        <span
          className={cn(
            'flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-xs font-medium',
            isActive
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground'
          )}
        >
          {badge}
        </span>
      )}
    </Link>
  )
}
