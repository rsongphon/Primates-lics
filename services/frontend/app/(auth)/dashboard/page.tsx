/**
 * Dashboard Page
 * Main dashboard with overview statistics and recent activity
 */

import { Metadata } from 'next'
import DashboardShell from '@/components/features/dashboard/DashboardShell'
import StatsCard from '@/components/features/dashboard/StatsCard'
import DashboardCard from '@/components/features/dashboard/DashboardCard'
import { Activity, BarChart3, Beaker, Cpu } from 'lucide-react'

export const metadata: Metadata = {
  title: 'Dashboard - LICS',
  description: 'Lab Instrument Control System Dashboard',
}

export default function DashboardPage() {
  // TODO: Replace with actual data from API
  const stats = {
    totalDevices: 24,
    activeExperiments: 8,
    completedTasks: 156,
    systemHealth: 98,
  }

  return (
    <DashboardShell
      heading="Dashboard"
      description="Welcome to LICS - Lab Instrument Control System"
    >
      {/* Statistics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Devices"
          value={stats.totalDevices}
          description="Connected devices"
          icon={Cpu}
          trend={{ value: 12, isPositive: true }}
        />
        <StatsCard
          title="Active Experiments"
          value={stats.activeExperiments}
          description="Currently running"
          icon={Beaker}
          trend={{ value: 3, isPositive: true }}
        />
        <StatsCard
          title="Completed Tasks"
          value={stats.completedTasks}
          description="This month"
          icon={Activity}
          trend={{ value: 8, isPositive: true }}
        />
        <StatsCard
          title="System Health"
          value={`${stats.systemHealth}%`}
          description="Overall status"
          icon={BarChart3}
          trend={{ value: 2, isPositive: true }}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7 mt-4">
        {/* Recent Activity */}
        <DashboardCard
          title="Recent Activity"
          description="Latest events across all devices"
          className="col-span-4"
        >
          <div className="space-y-4">
            {/* TODO: Replace with actual activity data */}
            <div className="flex items-center gap-4">
              <div className="w-2 h-2 bg-green-500 rounded-full" />
              <div className="flex-1">
                <p className="text-sm font-medium">Device-001 connected</p>
                <p className="text-xs text-muted-foreground">2 minutes ago</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-2 h-2 bg-blue-500 rounded-full" />
              <div className="flex-1">
                <p className="text-sm font-medium">Experiment started: EXP-123</p>
                <p className="text-xs text-muted-foreground">15 minutes ago</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-2 h-2 bg-purple-500 rounded-full" />
              <div className="flex-1">
                <p className="text-sm font-medium">Task completed: TASK-456</p>
                <p className="text-xs text-muted-foreground">1 hour ago</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-2 h-2 bg-yellow-500 rounded-full" />
              <div className="flex-1">
                <p className="text-sm font-medium">Device-005 requires attention</p>
                <p className="text-xs text-muted-foreground">3 hours ago</p>
              </div>
            </div>
          </div>
        </DashboardCard>

        {/* Quick Actions */}
        <DashboardCard
          title="Quick Actions"
          description="Common tasks and shortcuts"
          className="col-span-3"
        >
          <div className="space-y-2">
            <button className="w-full text-left px-4 py-2 rounded-md hover:bg-accent transition-colors">
              <p className="text-sm font-medium">New Experiment</p>
              <p className="text-xs text-muted-foreground">Start a new experiment</p>
            </button>
            <button className="w-full text-left px-4 py-2 rounded-md hover:bg-accent transition-colors">
              <p className="text-sm font-medium">Register Device</p>
              <p className="text-xs text-muted-foreground">Add a new device</p>
            </button>
            <button className="w-full text-left px-4 py-2 rounded-md hover:bg-accent transition-colors">
              <p className="text-sm font-medium">View Reports</p>
              <p className="text-xs text-muted-foreground">Access analytics</p>
            </button>
            <button className="w-full text-left px-4 py-2 rounded-md hover:bg-accent transition-colors">
              <p className="text-sm font-medium">Task Builder</p>
              <p className="text-xs text-muted-foreground">Create task templates</p>
            </button>
          </div>
        </DashboardCard>
      </div>

      {/* Device Overview */}
      <div className="grid gap-4 md:grid-cols-2 mt-4">
        <DashboardCard
          title="Device Overview"
          description="Status of connected devices"
        >
          <div className="space-y-3">
            {/* TODO: Replace with actual device data */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-green-500 rounded-full" />
                <span className="text-sm font-medium">Online</span>
              </div>
              <span className="text-sm text-muted-foreground">18 devices</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-yellow-500 rounded-full" />
                <span className="text-sm font-medium">Busy</span>
              </div>
              <span className="text-sm text-muted-foreground">4 devices</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-red-500 rounded-full" />
                <span className="text-sm font-medium">Offline</span>
              </div>
              <span className="text-sm text-muted-foreground">2 devices</span>
            </div>
          </div>
        </DashboardCard>

        <DashboardCard
          title="Experiment Status"
          description="Active and pending experiments"
        >
          <div className="space-y-3">
            {/* TODO: Replace with actual experiment data */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-blue-500 rounded-full" />
                <span className="text-sm font-medium">Running</span>
              </div>
              <span className="text-sm text-muted-foreground">8 experiments</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-purple-500 rounded-full" />
                <span className="text-sm font-medium">Pending</span>
              </div>
              <span className="text-sm text-muted-foreground">12 experiments</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-green-500 rounded-full" />
                <span className="text-sm font-medium">Completed</span>
              </div>
              <span className="text-sm text-muted-foreground">156 this month</span>
            </div>
          </div>
        </DashboardCard>
      </div>
    </DashboardShell>
  )
}
