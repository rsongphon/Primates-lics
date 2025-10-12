/**
 * Health Check Endpoint for Next.js Frontend
 *
 * Provides a simple health check endpoint for Docker healthcheck
 * and Kubernetes liveness/readiness probes.
 */

import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic'; // Disable caching for health checks

/**
 * GET /api/health
 * Basic health check endpoint
 */
export async function GET() {
  try {
    const healthData = {
      status: 'healthy',
      service: 'LICS Frontend',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      environment: process.env.NODE_ENV || 'development',
      version: '1.0.0',
    };

    return NextResponse.json(healthData, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      {
        status: 'unhealthy',
        service: 'LICS Frontend',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 503 }
    );
  }
}
