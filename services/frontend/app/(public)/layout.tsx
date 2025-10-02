import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: {
    template: '%s | LICS',
    default: 'LICS - Lab Instrument Control System',
  },
  description: 'Lab Instrument Control System - Manage your laboratory instruments and experiments',
};

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
