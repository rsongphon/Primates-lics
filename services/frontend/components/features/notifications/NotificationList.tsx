/**
 * Notification List
 * Container for displaying multiple notification toasts
 */

'use client'

import { useAppStore } from '@/lib/stores/app-store'
import NotificationToast from './NotificationToast'
import { cn } from '@/lib/utils'

interface NotificationListProps {
  className?: string
  maxVisible?: number
}

export default function NotificationList({ className, maxVisible = 5 }: NotificationListProps) {
  const { notifications, removeNotification, markNotificationAsRead } = useAppStore()

  // Get recent notifications
  const visibleNotifications = notifications.slice(0, maxVisible)

  if (visibleNotifications.length === 0) {
    return null
  }

  return (
    <div
      className={cn(
        'fixed right-4 top-20 z-50 flex w-full max-w-sm flex-col gap-2',
        className
      )}
      aria-live="polite"
      aria-label="Notifications"
    >
      {visibleNotifications.map((notification) => (
        <NotificationToast
          key={notification.id}
          id={notification.id}
          type={notification.type}
          title={notification.title}
          message={notification.message}
          timestamp={notification.timestamp}
          isRead={notification.isRead}
          onClose={removeNotification}
          onMarkRead={markNotificationAsRead}
        />
      ))}
    </div>
  )
}
