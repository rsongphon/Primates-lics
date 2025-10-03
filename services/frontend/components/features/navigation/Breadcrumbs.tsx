/**
 * Breadcrumbs
 * Navigation breadcrumb trail showing current page hierarchy
 */

'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight, Home } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BreadcrumbItem {
  label: string
  href: string
}

interface BreadcrumbsProps {
  className?: string
  homeHref?: string
}

export default function Breadcrumbs({ className, homeHref = '/dashboard' }: BreadcrumbsProps) {
  const pathname = usePathname()

  // Generate breadcrumb items from pathname
  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    if (!pathname || pathname === homeHref) return []

    const segments = pathname.split('/').filter(Boolean)
    const items: BreadcrumbItem[] = []

    segments.forEach((segment, index) => {
      const href = '/' + segments.slice(0, index + 1).join('/')
      const label = segment
        .split('-')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')

      items.push({ label, href })
    })

    return items
  }

  const breadcrumbs = generateBreadcrumbs()

  if (breadcrumbs.length === 0) {
    return null
  }

  return (
    <nav aria-label="Breadcrumb" className={cn('', className)}>
      <ol className="flex items-center gap-2 text-sm text-muted-foreground">
        {/* Home */}
        <li>
          <Link
            href={homeHref}
            className="flex items-center hover:text-foreground transition-colors"
          >
            <Home className="h-4 w-4" />
            <span className="sr-only">Home</span>
          </Link>
        </li>

        {/* Breadcrumb items */}
        {breadcrumbs.map((item, index) => {
          const isLast = index === breadcrumbs.length - 1

          return (
            <li key={item.href} className="flex items-center gap-2">
              <ChevronRight className="h-4 w-4" />
              {isLast ? (
                <span className="font-medium text-foreground" aria-current="page">
                  {item.label}
                </span>
              ) : (
                <Link
                  href={item.href}
                  className="hover:text-foreground transition-colors"
                >
                  {item.label}
                </Link>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
