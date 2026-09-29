import http from 'k6/http'
import { check, sleep } from 'k6'

// Run against the Ingress once it's deployed:
//   k6 run --vus 50 --duration 5m -e BASE_URL=http://civicpulse.local load/k6-script.js
//
// Capture `kubectl get hpa -w` in a second terminal while this runs, and
// chart replica count against elapsed time for the HPA lag question in
// docs/ENGINEERING-NOTES.md (§5.2 Q5).

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000'

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '2m', target: 50 },
    { duration: '2m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
  },
}

const SAMPLE_TEXTS = [
  'Burst water main flooding Street 12 since fajr, water entering ground floors',
  'Streetlight outage on the whole block, very dark at night',
  'Overflowing sewage near the market, bad smell for two days',
  'Pothole on the main road causing accidents during rain',
  'No electricity in the sector since yesterday evening',
]

export default function () {
  const text = SAMPLE_TEXTS[Math.floor(Math.random() * SAMPLE_TEXTS.length)]

  const createRes = http.post(
    `${BASE_URL}/api/complaints`,
    JSON.stringify({ text, location: `Sector ${Math.ceil(Math.random() * 20)}` }),
    { headers: { 'Content-Type': 'application/json' } },
  )
  check(createRes, {
    'complaint created (201) or rate-limited (429)': (r) => r.status === 201 || r.status === 429,
  })

  const listRes = http.get(`${BASE_URL}/api/complaints?page=1&page_size=20`)
  check(listRes, { 'list ok': (r) => r.status === 200 })

  const statsRes = http.get(`${BASE_URL}/api/stats`)
  check(statsRes, { 'stats ok': (r) => r.status === 200 })

  sleep(1)
}
