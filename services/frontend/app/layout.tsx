import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { Providers } from '@/lib/providers';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });

export const metadata: Metadata = {
  title: 'LICS - Lab Instrument Control System',
  description:
    'Cloud-native platform for managing laboratory instruments and conducting behavioral experiments',
  keywords: [
    'laboratory',
    'instrument control',
    'experiment management',
    'behavioral research',
    'neuroscience',
    'automation',
  ],
  authors: [
    {
      name: 'LICS Team',
      url: 'https://github.com/rsongphon/Primates-lics',
    },
  ],
  creator: 'LICS Team',
  publisher: 'LICS',
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://lics.io',
    title: 'LICS - Lab Instrument Control System',
    description:
      'Cloud-native platform for managing laboratory instruments and conducting behavioral experiments',
    siteName: 'LICS',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.variable}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
