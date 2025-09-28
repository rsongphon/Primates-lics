// K6 Performance Test for LICS API
// Based on Documentation.md Section 16.4 - Performance Testing

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiResponseTime = new Trend('api_response_time');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 5 },   // Ramp up to 5 users
    { duration: '1m', target: 10 },   // Stay at 10 users
    { duration: '30s', target: 20 },  // Ramp up to 20 users
    { duration: '2m', target: 20 },   // Stay at 20 users
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'], // 95% of requests under 200ms
    http_req_failed: ['rate<0.1'],    // Error rate under 10%
    errors: ['rate<0.1'],             // Custom error rate under 10%
  },
};

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-api-key';

// Setup function - runs once before test starts
export function setup() {
  console.log(`Starting performance test against: ${BASE_URL}`);

  // Perform authentication to get token
  const authResponse = http.post(`${BASE_URL}/api/v1/auth/login`, {
    email: 'test@example.com',
    password: 'testpassword123'
  }, {
    headers: { 'Content-Type': 'application/json' },
  });

  const authToken = authResponse.json('access_token');

  return {
    authToken: authToken,
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json',
    },
  };
}

// Main test function
export default function(data) {
  const { headers } = data;

  // Test 1: Health check endpoint
  const healthResponse = http.get(`${BASE_URL}/health`);
  check(healthResponse, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 50ms': (r) => r.timings.duration < 50,
  });
  apiResponseTime.add(healthResponse.timings.duration);
  errorRate.add(healthResponse.status !== 200);

  sleep(0.1);

  // Test 2: Get organizations
  const orgsResponse = http.get(`${BASE_URL}/api/v1/organizations`, { headers });
  check(orgsResponse, {
    'organizations status is 200': (r) => r.status === 200,
    'organizations response time < 200ms': (r) => r.timings.duration < 200,
    'organizations returns array': (r) => Array.isArray(r.json()),
  });
  apiResponseTime.add(orgsResponse.timings.duration);
  errorRate.add(orgsResponse.status !== 200);

  sleep(0.2);

  // Test 3: Get devices
  const devicesResponse = http.get(`${BASE_URL}/api/v1/devices`, { headers });
  check(devicesResponse, {
    'devices status is 200': (r) => r.status === 200,
    'devices response time < 200ms': (r) => r.timings.duration < 200,
  });
  apiResponseTime.add(devicesResponse.timings.duration);
  errorRate.add(devicesResponse.status !== 200);

  sleep(0.2);

  // Test 4: Get experiments
  const experimentsResponse = http.get(`${BASE_URL}/api/v1/experiments`, { headers });
  check(experimentsResponse, {
    'experiments status is 200': (r) => r.status === 200,
    'experiments response time < 200ms': (r) => r.timings.duration < 200,
  });
  apiResponseTime.add(experimentsResponse.timings.duration);
  errorRate.add(experimentsResponse.status !== 200);

  sleep(0.3);

  // Test 5: Create and delete a test device (write operations)
  const devicePayload = {
    name: `test-device-${__VU}-${__ITER}`,
    type: 'raspberry-pi',
    location: 'lab-test',
    capabilities: {
      sensors: ['temperature', 'humidity'],
      actuators: ['led', 'buzzer']
    }
  };

  const createResponse = http.post(`${BASE_URL}/api/v1/devices`, JSON.stringify(devicePayload), { headers });
  const createSuccess = check(createResponse, {
    'device creation status is 201': (r) => r.status === 201,
    'device creation response time < 300ms': (r) => r.timings.duration < 300,
    'device creation returns id': (r) => r.json('id') !== undefined,
  });
  apiResponseTime.add(createResponse.timings.duration);
  errorRate.add(createResponse.status !== 201);

  // Clean up - delete the created device
  if (createSuccess && createResponse.json('id')) {
    const deviceId = createResponse.json('id');
    const deleteResponse = http.del(`${BASE_URL}/api/v1/devices/${deviceId}`, null, { headers });
    check(deleteResponse, {
      'device deletion status is 204': (r) => r.status === 204,
      'device deletion response time < 200ms': (r) => r.timings.duration < 200,
    });
    apiResponseTime.add(deleteResponse.timings.duration);
    errorRate.add(deleteResponse.status !== 204);
  }

  sleep(0.5);
}

// Teardown function - runs once after test completes
export function teardown(data) {
  console.log('Performance test completed');

  // Log out if needed
  if (data.authToken) {
    http.post(`${BASE_URL}/api/v1/auth/logout`, null, {
      headers: { 'Authorization': `Bearer ${data.authToken}` },
    });
  }
}