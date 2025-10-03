/**
 * useBreadcrumbs Hook
 * Custom hook for managing breadcrumb state and providing custom breadcrumb items
 */

import { useMemo } from 'react'
import { usePathname } from 'next/navigation'

export interface BreadcrumbItem {
  label: string
  href: string
}

interface BreadcrumbConfig {
  [path: string]: BreadcrumbItem[]
}

// Custom breadcrumb configurations for specific routes
const customBreadcrumbs: BreadcrumbConfig = {
  '/dashboard': [],
  '/devices': [{ label: 'Devices', href: '/devices' }],
  '/experiments': [{ label: 'Experiments', href: '/experiments' }],
  '/tasks': [{ label: 'Tasks', href: '/tasks' }],
  '/participants': [{ label: 'Participants', href: '/participants' }],
  '/reports': [{ label: 'Reports', href: '/reports' }],
  '/settings': [{ label: 'Settings', href: '/settings' }],
  '/profile': [{ label: 'Profile', href: '/profile' }],
}

export function useBreadcrumbs(customItems?: BreadcrumbItem[]): BreadcrumbItem[] {
  const pathname = usePathname()

  return useMemo(() => {
    // If custom items provided, use them
    if (customItems && customItems.length > 0) {
      return customItems
    }

    // Check if we have a custom configuration for this exact path
    if (customBreadcrumbs[pathname]) {
      return customBreadcrumbs[pathname]
    }

    // Generate breadcrumbs from pathname
    if (!pathname || pathname === '/dashboard') {
      return []
    }

    const segments = pathname.split('/').filter(Boolean)
    const items: BreadcrumbItem[] = []

    segments.forEach((segment, index) => {
      const href = '/' + segments.slice(0, index + 1).join('/')

      // Convert segment to title case (handle kebab-case and snake_case)
      const label = segment
        .replace(/[-_]/g, ' ')
        .split(' ')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')

      items.push({ label, href })
    })

    return items
  }, [pathname, customItems])
}

/**
 * Helper function to create breadcrumb items programmatically
 */
export function createBreadcrumbs(items: Array<{ label: string; href: string }>): BreadcrumbItem[] {
  return items.map((item) => ({
    label: item.label,
    href: item.href,
  }))
}

/**
 * Helper function to get breadcrumbs for a specific entity (e.g., device, experiment)
 */
export function getEntityBreadcrumbs(
  entityType: string,
  entityId: string,
  entityName: string
): BreadcrumbItem[] {
  const basePath = `/${entityType}s` // e.g., /devices, /experiments

  return [
    {
      label: entityType.charAt(0).toUpperCase() + entityType.slice(1) + 's',
      href: basePath,
    },
    {
      label: entityName,
      href: `${basePath}/${entityId}`,
    },
  ]
}
