'use client';

import { useState } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface MainShellProps {
  children: React.ReactNode;
}

export function MainShell({ children }: MainShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="relative flex min-h-screen flex-col">
      {/* Header */}
      <Header />

      <div className="flex flex-1">
        {/* Desktop Sidebar */}
        <div className="hidden lg:block">
          <Sidebar />
        </div>

        {/* Mobile Sidebar Overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Mobile Sidebar Drawer */}
        <div
          className={cn(
            'fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out lg:hidden',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          <Sidebar />
        </div>

        {/* Main Content */}
        <main className="flex-1">
          {/* Mobile Menu Button */}
          <div className="sticky top-16 z-30 border-b bg-background p-4 lg:hidden">
            <Button variant="outline" size="sm" onClick={() => setSidebarOpen(!sidebarOpen)}>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="mr-2"
              >
                <line x1="4" x2="20" y1="12" y2="12" />
                <line x1="4" x2="20" y1="6" y2="6" />
                <line x1="4" x2="20" y1="18" y2="18" />
              </svg>
              Menu
            </Button>
          </div>

          {/* Page Content */}
          <div className="container mx-auto p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
