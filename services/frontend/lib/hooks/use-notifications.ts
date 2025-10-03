/**
 * useNotifications Hook
 * Simplified hook for managing notifications
 */

import { useAppStore } from '@/lib/stores/app-store'
import type { NotificationType } from '@/components/features/notifications/NotificationToast'

export interface NotificationOptions {
  title: string
  message: string
  type?: NotificationType
  duration?: number // Auto-dismiss after duration (ms), 0 = no auto-dismiss
}

export function useNotifications() {
  const { notifications, addNotification, removeNotification, markNotificationAsRead, clearNotifications } =
    useAppStore()

  /**
   * Show a notification
   */
  const show = (options: NotificationOptions) => {
    const notification = {
      id: `notification-${Date.now()}-${Math.random()}`,
      type: options.type || 'info',
      title: options.title,
      message: options.message,
      timestamp: new Date(),
      isRead: false,
    }

    addNotification(notification)

    // Auto-dismiss if duration specified
    if (options.duration && options.duration > 0) {
      setTimeout(() => {
        removeNotification(notification.id)
      }, options.duration)
    }

    return notification.id
  }

  /**
   * Show an info notification
   */
  const info = (title: string, message: string, duration?: number) => {
    return show({ title, message, type: 'info', duration })
  }

  /**
   * Show a success notification
   */
  const success = (title: string, message: string, duration?: number) => {
    return show({ title, message, type: 'success', duration })
  }

  /**
   * Show a warning notification
   */
  const warning = (title: string, message: string, duration?: number) => {
    return show({ title, message, type: 'warning', duration })
  }

  /**
   * Show an error notification
   */
  const error = (title: string, message: string, duration?: number) => {
    return show({ title, message, type: 'error', duration })
  }

  /**
   * Dismiss a notification by ID
   */
  const dismiss = (id: string) => {
    removeNotification(id)
  }

  /**
   * Mark a notification as read
   */
  const markRead = (id: string) => {
    markNotificationAsRead(id)
  }

  /**
   * Clear all notifications
   */
  const clearAll = () => {
    clearNotifications()
  }

  /**
   * Get unread count
   */
  const unreadCount = notifications.filter((n) => !n.isRead).length

  return {
    notifications,
    unreadCount,
    show,
    info,
    success,
    warning,
    error,
    dismiss,
    markRead,
    clearAll,
  }
}
