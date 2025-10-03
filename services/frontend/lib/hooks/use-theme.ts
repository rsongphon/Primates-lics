/**
 * useTheme Hook
 * Hook for managing theme (light/dark mode) with persistence
 */

'use client'

import { useEffect } from 'react'
import { useAppStore } from '@/lib/stores/app-store'

export type Theme = 'light' | 'dark'

export function useTheme() {
  const { theme, setTheme } = useAppStore()

  // Apply theme class to document root on mount and theme change
  useEffect(() => {
    const root = document.documentElement

    // Remove previous theme classes
    root.classList.remove('light', 'dark')

    // Add current theme class
    root.classList.add(theme)

    // Update meta theme-color
    const metaThemeColor = document.querySelector('meta[name="theme-color"]')
    if (metaThemeColor) {
      metaThemeColor.setAttribute(
        'content',
        theme === 'dark' ? '#0f172a' : '#ffffff'
      )
    }
  }, [theme])

  /**
   * Toggle between light and dark mode
   */
  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }

  /**
   * Set theme to light mode
   */
  const setLightMode = () => {
    setTheme('light')
  }

  /**
   * Set theme to dark mode
   */
  const setDarkMode = () => {
    setTheme('dark')
  }

  /**
   * Check if dark mode is active
   */
  const isDark = theme === 'dark'

  /**
   * Check if light mode is active
   */
  const isLight = theme === 'light'

  return {
    theme,
    setTheme,
    toggleTheme,
    setLightMode,
    setDarkMode,
    isDark,
    isLight,
  }
}
