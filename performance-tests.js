import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 }, // Ramp up
    { duration: '5m', target: 10 }, // Stay at 10 users
    { duration: '2m', target: 20 }, // Ramp up to 20 users
    { duration: '5m', target: 20 }, // Stay at 20 users
    { duration: '2m', target: 0 },  // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests must complete below 2s
    http_req_failed: ['rate<0.1'],     // Error rate must be below 10%
  },
};

const BASE_URL = 'http://localhost:3000';

export default function() {
  // Test main page load
  let response = http.get(BASE_URL);
  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
    'has PWA manifest': (r) => r.body.includes('manifest.json'),
    'has service worker': (r) => r.body.includes('sw.js'),
  });

  sleep(1);

  // Test API endpoints
  const apiEndpoints = [
    '/get_benchmark_data',
    '/get_news',
    '/refresh_all_markets'
  ];

  for (let endpoint of apiEndpoints) {
    let apiResponse = http.get(`${BASE_URL}${endpoint}`);
    check(apiResponse, {
      'API status is 200': (r) => r.status === 200,
      'API response time < 1s': (r) => r.timings.duration < 1000,
    });
    sleep(0.5);
  }

  // Test PWA resources
  const pwaResources = [
    '/static/sw.js',
    '/manifest.json',
    '/static/icon-192x192.png',
    '/static/icon-512x512.png'
  ];

  for (let resource of pwaResources) {
    let resourceResponse = http.get(`${BASE_URL}${resource}`);
    check(resourceResponse, {
      'Resource status is 200': (r) => r.status === 200,
      'Resource response time < 500ms': (r) => r.timings.duration < 500,
    });
    sleep(0.2);
  }
}
