/**
 * k6 load test for the GraphQL gateway.
 *
 * Run:
 *   k6 run tests/load/k6-gateway.js
 *   k6 run --env GATEWAY_URL=http://localhost:8000 tests/load/k6-gateway.js
 */

import http from "k6/http";
import { check, sleep } from "k6";

const GATEWAY_URL = __ENV.GATEWAY_URL || "http://localhost:8000";
const GRAPHQL_ENDPOINT = `${GATEWAY_URL}/graphql`;

export const options = {
  scenarios: {
    smoke: {
      executor: "constant-vus",
      vus: 1,
      duration: "30s",
      gracefulStop: "5s",
      tags: { scenario: "smoke" },
    },
    load: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m", target: 10 },
        { duration: "2m", target: 50 },
        { duration: "1m", target: 50 },
        { duration: "1m", target: 0 },
      ],
      startTime: "35s",
      gracefulStop: "10s",
      tags: { scenario: "load" },
    },
    stress: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m", target: 50 },
        { duration: "2m", target: 200 },
        { duration: "1m", target: 200 },
        { duration: "1m", target: 0 },
      ],
      startTime: "6m",
      gracefulStop: "10s",
      tags: { scenario: "stress" },
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<500"],
    http_req_failed: ["rate<0.01"],
    "http_req_duration{name:ListAgents}": ["p(95)<400"],
    "http_req_duration{name:SendMessage}": ["p(95)<800"],
  },
};

const headers = { "Content-Type": "application/json" };

function graphql(query, variables, name) {
  const payload = JSON.stringify({ query, variables });
  const res = http.post(GRAPHQL_ENDPOINT, payload, {
    headers,
    tags: { name },
  });

  check(res, {
    "status is 200": (r) => r.status === 200,
    "no GraphQL errors": (r) => {
      const body = r.json();
      return !body.errors || body.errors.length === 0;
    },
  });

  return res;
}

export default function () {
  // ListAgents query (more frequent)
  graphql(
    `query ListAgents {
      agents {
        id
        name
        description
        status
      }
    }`,
    null,
    "ListAgents"
  );

  sleep(0.5);

  // SendMessage mutation
  graphql(
    `mutation SendMessage($input: SendMessageInput!) {
      sendMessage(input: $input) {
        id
        content
        role
        timestamp
      }
    }`,
    {
      input: {
        agentId: "default-agent",
        content: "Summarize the latest report.",
        sessionId: `k6-session-${__VU}`,
      },
    },
    "SendMessage"
  );

  sleep(1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: "  ", enableColors: true }),
    "results/k6-gateway-summary.json": JSON.stringify(data, null, 2),
  };
}

// k6 built-in text summary helper
import { textSummary } from "https://jslib.k6.io/k6-summary/0.1.0/index.js";
