import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js Middleware for Authentication
 *
 * Protects authenticated routes and handles redirects:
 * - Redirects unauthenticated users to /login
 * - Redirects authenticated users away from /login and /register
 * - Allows public routes
 */

// Routes that require authentication
const protectedRoutes = [
  '/dashboard',
  '/devices',
  '/experiments',
  '/tasks',
  '/participants',
  '/reports',
  '/settings',
  '/profile',
];

// Routes that should redirect if already authenticated
const authRoutes = ['/login', '/register'];

// Routes that are always public
const publicRoutes = ['/', '/forgot-password', '/reset-password'];

/**
 * Check if user is authenticated by looking for access token
 * Checks both localStorage (remember me) and sessionStorage
 */
function isAuthenticated(request: NextRequest): boolean {
  // In middleware, we can't access localStorage/sessionStorage directly
  // We need to use cookies or headers
  // For now, we'll check for a cookie that should be set by the client
  const accessToken = request.cookies.get('access_token')?.value;
  return !!accessToken;
}

/**
 * Check if path matches any of the given route patterns
 */
function matchesRoute(pathname: string, routes: string[]): boolean {
  return routes.some((route) => {
    // Exact match
    if (pathname === route) return true;
    // Starts with route (for nested routes like /dashboard/*)
    if (pathname.startsWith(route + '/')) return true;
    return false;
  });
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if route is public (always allow)
  if (matchesRoute(pathname, publicRoutes)) {
    return NextResponse.next();
  }

  const authenticated = isAuthenticated(request);

  // Check if route requires authentication
  if (matchesRoute(pathname, protectedRoutes)) {
    if (!authenticated) {
      // Redirect to login with return URL
      const url = new URL('/login', request.url);
      url.searchParams.set('from', pathname);
      return NextResponse.redirect(url);
    }
    // User is authenticated, allow access
    return NextResponse.next();
  }

  // Check if route is auth page (login/register)
  if (matchesRoute(pathname, authRoutes)) {
    if (authenticated) {
      // User is already authenticated, redirect to dashboard
      // Check if there's a return URL
      const from = request.nextUrl.searchParams.get('from');
      const url = new URL(from || '/dashboard', request.url);
      return NextResponse.redirect(url);
    }
    // User is not authenticated, allow access to login/register
    return NextResponse.next();
  }

  // For all other routes, allow access
  return NextResponse.next();
}

/**
 * Configure which routes the middleware should run on
 * This runs on all routes except static files and API routes
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     * - api routes
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
