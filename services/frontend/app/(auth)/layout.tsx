/**
 * Authenticated Layout
 * Layout for all authenticated pages with sidebar and header
 */

import MainShell from '@/components/shared/MainShell'

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <MainShell>{children}</MainShell>
}
