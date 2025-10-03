/**
 * Notification Toast
 * Individual notification toast component with types and actions
 */

'use client'

import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

export type NotificationType = 'info' | 'success' | 'warning' | 'error'

export interface NotificationToastProps {
  id: string
  type: NotificationType
  title: string
  message: string
  timestamp: Date
  isRead: boolean
  onClose: (id: string) => void
  onMarkRead: (id: string) => void
}

const typeStyles: Record<NotificationType, string> = {
  info: 'border-blue-500 bg-blue-50 text-blue-900 dark:bg-blue-950 dark:text-blue-100',
  success: 'border-green-500 bg-green-50 text-green-900 dark:bg-green-950 dark:text-green-100',
  warning: 'border-yellow-500 bg-yellow-50 text-yellow-900 dark:bg-yellow-950 dark:text-yellow-100',
  error: 'border-red-500 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100',
}

export default function NotificationToast({
  id,
  type,
  title,
  message,
  timestamp,
  isRead,
  onClose,
  onMarkRead,
}: NotificationToastProps) {
  const handleClick = () => {
    if (!isRead) {
      onMarkRead(id)
    }
  }

  const formatTimestamp = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return 'Just now'
  }

  return (
    <div
      className={cn(
        'relative flex gap-3 rounded-lg border-l-4 p-4 shadow-md transition-all cursor-pointer',
        typeStyles[type],
        !isRead && 'font-medium'
      )}
      onClick={handleClick}
      role="alert"
      aria-live="polite"
    >
      {/* Unread Indicator */}
      {!isRead && (
        <div className="absolute top-2 left-2 h-2 w-2 rounded-full bg-current" />
      )}

      {/* Content */}
      <div className="flex-1 space-y-1">
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-sm opacity-90">{message}</p>
        <p className="text-xs opacity-70">{formatTimestamp(timestamp)}</p>
      </div>

      {/* Close Button */}
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 flex-shrink-0"
        onClick={(e) => {
          e.stopPropagation()
          onClose(id)
        }}
        aria-label="Close notification"
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}
