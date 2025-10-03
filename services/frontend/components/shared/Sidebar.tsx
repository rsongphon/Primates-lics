'use client'

import { cn } from '@/lib/utils'
import { Separator } from '@/components/ui/separator'
import NavItem from '@/components/features/navigation/NavItem'
import NavSection from '@/components/features/navigation/NavSection'
import {
  LayoutDashboard,
  Cpu,
  Beaker,
  Target,
  Settings,
  HelpCircle,
  FileText,
  Users,
} from 'lucide-react'

const mainNavItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/devices', label: 'Devices', icon: Cpu, badge: 3 },
  { href: '/experiments', label: 'Experiments', icon: Beaker },
  { href: '/tasks', label: 'Tasks', icon: Target },
  { href: '/participants', label: 'Participants', icon: Users },
  { href: '/reports', label: 'Reports', icon: FileText },
]

const settingsNavItems = [
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/help', label: 'Help', icon: HelpCircle },
]

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  return (
    <aside className={cn('flex h-full w-64 flex-col border-r bg-background', className)}>
      {/* Organization Info */}
      <div className="p-6">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
            <span className="text-lg font-bold text-primary-foreground">L</span>
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold">LICS Platform</p>
            <p className="text-xs text-muted-foreground">Main Organization</p>
          </div>
        </div>
      </div>

      <Separator />

      {/* Main Navigation */}
      <nav className="flex-1 space-y-4 p-4">
        {/* Main Section */}
        <NavSection heading="Main">
          {mainNavItems.map((item) => (
            <NavItem
              key={item.href}
              href={item.href}
              label={item.label}
              icon={item.icon}
              badge={item.badge}
            />
          ))}
        </NavSection>

        <Separator className="my-2" />

        {/* Settings Section */}
        <NavSection heading="Settings">
          {settingsNavItems.map((item) => (
            <NavItem
              key={item.href}
              href={item.href}
              label={item.label}
              icon={item.icon}
            />
          ))}
        </NavSection>
      </nav>

      {/* Footer Section */}
      <div className="border-t p-4">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Version 1.0.0</span>
          <div className="flex items-center space-x-1">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            <span>Online</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
