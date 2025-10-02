import Link from 'next/link';
import { Separator } from '@/components/ui/separator';

const footerLinks = {
  product: [
    { label: 'Features', href: '/features' },
    { label: 'Documentation', href: '/docs' },
    { label: 'API Reference', href: '/api-docs' },
    { label: 'Changelog', href: '/changelog' },
  ],
  support: [
    { label: 'Help Center', href: '/help' },
    { label: 'Contact Us', href: '/contact' },
    { label: 'Status', href: '/status' },
    { label: 'Report Issue', href: '/issues' },
  ],
  legal: [
    { label: 'Privacy Policy', href: '/privacy' },
    { label: 'Terms of Service', href: '/terms' },
    { label: 'Cookie Policy', href: '/cookies' },
    { label: 'License', href: '/license' },
  ],
};

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t bg-background">
      <div className="container py-8">
        {/* Footer Links */}
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                <span className="text-lg font-bold text-primary-foreground">L</span>
              </div>
              <span className="font-bold">LICS</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Lab Instrument Control System - Cloud-native platform for managing laboratory
              instruments and conducting behavioral experiments.
            </p>
          </div>

          {/* Product Links */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold">Product</h4>
            <ul className="space-y-2">
              {footerLinks.product.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Support Links */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold">Support</h4>
            <ul className="space-y-2">
              {footerLinks.support.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal Links */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold">Legal</h4>
            <ul className="space-y-2">
              {footerLinks.legal.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <Separator className="my-6" />

        {/* Footer Bottom */}
        <div className="flex flex-col items-center justify-between space-y-4 md:flex-row md:space-y-0">
          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
            <span>© {currentYear} LICS. All rights reserved.</span>
            <span className="hidden md:inline">•</span>
            <span className="hidden md:inline">Version 1.0.0-alpha</span>
          </div>

          {/* System Status */}
          <div className="flex items-center space-x-2 text-sm">
            <div className="flex items-center space-x-1 text-muted-foreground">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span>All Systems Operational</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
