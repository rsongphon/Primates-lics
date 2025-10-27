/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    // API Gateway (Kong) URLs - All traffic goes through Kong
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080',

    // Direct backend URLs (for bypass/debugging)
    NEXT_PUBLIC_BACKEND_DIRECT_URL: process.env.NEXT_PUBLIC_BACKEND_DIRECT_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_DIRECT_URL: process.env.NEXT_PUBLIC_WS_DIRECT_URL || 'ws://localhost:8001',
  },
  images: {
    domains: ['localhost'],
  },
  // Experimental features can be enabled as routes are implemented
  // experimental: {
  //   typedRoutes: true,
  // },
};

module.exports = nextConfig;
