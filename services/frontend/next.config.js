/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001',
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
