# LICS Frontend

[![Frontend CI](https://github.com/rsongphon/Primates-lics/workflows/Frontend%20CI/badge.svg)](https://github.com/rsongphon/Primates-lics/actions)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-blue.svg)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org/)

The LICS frontend is a modern web application built with Next.js 14, providing an intuitive interface for laboratory instrument control and experiment management.

## 📊 Implementation Status

**Last Updated**: October 2, 2025
**Current Phase**: Phase 3 - Frontend Development (Week 5, Day 1-2 ✅ COMPLETED)

### ✅ Completed
- ✅ Next.js 14.2.13 with TypeScript 5.3.3 (strict mode)
- ✅ Tailwind CSS 3.4.1 with custom LICS theme
- ✅ Shadcn/ui component library (15 components installed)
- ✅ ESLint and Prettier configuration
- ✅ Path aliases and project structure
- ✅ Base layout components (Header, Sidebar, MainShell, Footer, Loading, ErrorBoundary)
- ✅ All tests passing (typecheck, lint, format, build)

### 🔄 In Progress
- State Management (Zustand stores)
- API client implementation
- Authentication flow

### 📝 Planned
- Dashboard pages
- Device management UI
- Experiment management UI
- Task builder with React Flow
- Testing infrastructure (Jest, Playwright)

## 🛠️ Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Shadcn/ui
- **State Management**: Zustand
- **Data Fetching**: React Query (TanStack Query)
- **Real-time**: Socket.IO client
- **Task Builder**: React Flow
- **Charts**: Recharts
- **Forms**: React Hook Form with Zod validation

## 🚀 Quick Start

### Prerequisites

- Node.js 20+ and npm
- Access to LICS backend API

### Development Setup

1. **Install dependencies**

   ```bash
   npm install
   ```

2. **Environment Configuration**

   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

3. **Start development server**

   ```bash
   npm run dev
   ```

4. **Open browser**
   ```
   http://localhost:3000
   ```

### Environment Variables

Create a `.env.local` file with the following variables:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8001

# Authentication
NEXT_PUBLIC_AUTH_ENABLED=true

# Features
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_VIDEO_STREAMING=true

# Development
NEXT_PUBLIC_DEBUG=false
```

## 📁 Project Structure

```
services/frontend/
├── app/                    # Next.js 14 App Router
│   ├── (auth)/            # Protected routes
│   │   ├── dashboard/     # Main dashboard
│   │   ├── devices/       # Device management
│   │   ├── experiments/   # Experiment management
│   │   └── tasks/         # Task builder
│   ├── (public)/          # Public routes
│   │   ├── login/         # Authentication
│   │   └── register/      # User registration
│   ├── api/               # API routes
│   ├── globals.css        # Global styles
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── components/            # React components
│   ├── ui/               # Base UI components (Shadcn)
│   ├── features/         # Feature-specific components
│   └── shared/           # Shared components
├── lib/                  # Utility libraries
│   ├── api/             # API client functions
│   ├── hooks/           # Custom React hooks
│   ├── stores/          # Zustand stores
│   ├── utils/           # Utility functions
│   └── validations/     # Zod schemas
├── public/              # Static assets
├── styles/              # Additional styles
└── types/               # TypeScript type definitions
```

## 🧩 Key Features

### Dashboard

- Real-time system overview
- Device status monitoring
- Experiment progress tracking
- System health indicators

### Device Management

- Device discovery and registration
- Real-time status monitoring
- Configuration management
- GPIO pin mapping
- Video streaming integration

### Experiment Management

- Experiment creation wizard
- Participant management
- Progress monitoring
- Data visualization
- Results export

### Task Builder

- Visual flow editor using React Flow
- Drag-and-drop interface
- Node-based task creation
- Real-time validation
- Template library

### Real-time Features

- WebSocket integration for live updates
- Real-time device status
- Live experiment monitoring
- System notifications

## 🎨 UI Components

We use Shadcn/ui for our component system. All components are:

- Fully accessible
- Dark mode compatible
- Customizable with CSS variables
- TypeScript enabled

### Adding New Components

```bash
# Add a new Shadcn component
npx shadcn-ui@latest add button

# Create a custom component
npx create-component MyComponent
```

## 📊 State Management

### Zustand Stores

We use Zustand for state management with the following stores:

- **`useAppStore`**: Global application state
- **`useAuthStore`**: Authentication state
- **`useDeviceStore`**: Device management state
- **`useExperimentStore`**: Experiment state
- **`useTaskStore`**: Task builder state

### Example Store Usage

```typescript
import { useDeviceStore } from '@/lib/stores/device-store'

function DeviceList() {
  const { devices, fetchDevices, isLoading } = useDeviceStore()

  useEffect(() => {
    fetchDevices()
  }, [fetchDevices])

  if (isLoading) return <LoadingSpinner />

  return (
    <div>
      {devices.map(device => (
        <DeviceCard key={device.id} device={device} />
      ))}
    </div>
  )
}
```

## 🔄 Data Fetching

We use React Query for server state management:

```typescript
import { useQuery } from '@tanstack/react-query';
import { getDevices } from '@/lib/api/devices';

function useDevices() {
  return useQuery({
    queryKey: ['devices'],
    queryFn: getDevices,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
  });
}
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
```

### Test Structure

- **Unit Tests**: Components and utilities
- **Integration Tests**: Feature workflows
- **E2E Tests**: Full user journeys with Playwright

### Writing Tests

```typescript
import { render, screen } from '@testing-library/react'
import { DeviceCard } from './device-card'

describe('DeviceCard', () => {
  it('displays device information correctly', () => {
    const device = {
      id: '1',
      name: 'Test Device',
      status: 'online'
    }

    render(<DeviceCard device={device} />)

    expect(screen.getByText('Test Device')).toBeInTheDocument()
    expect(screen.getByText('online')).toBeInTheDocument()
  })
})
```

## 🎭 Styling

### Tailwind CSS

We use Tailwind CSS for styling with a custom design system:

```typescript
// Example component with Tailwind classes
export function Button({ variant = 'primary', children, ...props }) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-md text-sm font-medium',
        'transition-colors focus-visible:outline-none focus-visible:ring-2',
        {
          'bg-primary text-primary-foreground hover:bg-primary/90': variant === 'primary',
          'bg-secondary text-secondary-foreground hover:bg-secondary/80': variant === 'secondary',
        }
      )}
      {...props}
    >
      {children}
    </button>
  )
}
```

### CSS Variables

Our design system uses CSS variables for theming:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --primary: 221.2 83.2% 53.3%;
  --primary-foreground: 210 40% 98%;
  /* ... more variables */
}
```

## 🔌 Real-time Integration

### WebSocket Connection

```typescript
import { useEffect } from 'react';
import { io } from 'socket.io-client';

export function useWebSocket() {
  useEffect(() => {
    const socket = io(process.env.NEXT_PUBLIC_WS_URL);

    socket.on('device_status', (data) => {
      // Handle real-time device updates
    });

    socket.on('experiment_update', (data) => {
      // Handle experiment updates
    });

    return () => socket.disconnect();
  }, []);
}
```

## 📱 Responsive Design

The application is fully responsive and supports:

- Desktop (1024px+)
- Tablet (768px - 1024px)
- Mobile (320px - 768px)

## ♿ Accessibility

We follow WCAG 2.1 AA guidelines:

- Semantic HTML
- Keyboard navigation
- Screen reader support
- Color contrast compliance
- Focus management

## 🚀 Building for Production

```bash
# Build the application
npm run build

# Start production server
npm start

# Export static files (if applicable)
npm run export
```

### Performance Optimization

- **Code Splitting**: Automatic route-based splitting
- **Image Optimization**: Next.js Image component
- **Bundle Analysis**: `npm run analyze`
- **Caching**: Efficient caching strategies

## 🐛 Debugging

### Development Tools

```bash
# Enable debug mode
NEXT_PUBLIC_DEBUG=true npm run dev

# Analyze bundle size
npm run analyze

# Type checking
npm run type-check

# Linting
npm run lint
```

### Browser DevTools

- React Developer Tools
- React Query DevTools
- Zustand DevTools

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Shadcn/ui Documentation](https://ui.shadcn.com/)
- [React Query Documentation](https://tanstack.com/query/latest)

## 🤝 Contributing

1. Follow the component structure conventions
2. Write tests for new features
3. Update documentation
4. Follow the established code style
5. Ensure accessibility compliance

See the main [Contributing Guide](../../CONTRIBUTING.md) for more details.
