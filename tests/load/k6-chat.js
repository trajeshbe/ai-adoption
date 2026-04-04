/**
 * k6 load test for the chat endpoint.
 *
 * Simulates concurrent chat sessions and measures:
 * - Time to first token (TTFT)
 * - Total response time
 *
 * Run:
 *   k6 run tests/load/k6-chat.js
 *   k6 run --env GATEWAY_URL=http://localhost:8000 tests/load/k6-chat.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Trend, Counter, Rate } from "k6/metrics";

const GATEWAY_URL = __ENV.GATEWAY_URL || "http://localhost:8000";
const GRAPHQL_ENDPOINT = `${GATEWAY_URL}/graphql`;

// Custom metrics
const timeToFirstToken = new Trend("chat_time_to_first_token", true);
const totalResponseTime = new Trend("chat_total_response_time", true);
const chatSuccess = new Rate("chat_success_rate");
const chatMessages = new Counter("chat_messages_total");

export const options = {
  scenarios: {
    concurrent_chats: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 10 },
        { duration: "1m", target: 25 },
        { duration: "1m", target: 50 },
        { duration: "30s", target: 50 },
        { duration: "1m", target: 0 },
      ],
      gracefulStop: "15s",
    },
    sustained_sessions: {
      executor: "constant-vus",
      vus: 10,
      duration: "3m",
      startTime: "4m",
      gracefulStop: "10s",
    },
  },
  thresholds: {
    chat_time_to_first_token: ["p(95)<2000", "p(99)<5000"],
    chat_total_response_time: ["p(95)<10000", "p(99)<30000"],
    chat_success_rate: ["rate>0.95"],
    http_req_failed: ["rate<0.05"],
  },
};

const headers = { "Content-Type": "application/json" };

const PROMPTS = [
  "Explain microservices architecture in three sentences.",
  "What are the SOLID principles?",
  "How does Kubernetes handle pod scheduling?",
  "Describe the CAP theorem.",
  "What is the difference between gRPC and REST?",
  "Explain event sourcing and CQRS.",
  "How do circuit breakers work in distributed systems?",
  "What are the benefits of GitOps?",
];

function getRandomPrompt() {
  return PROMPTS[Math.floor(Math.random() * PROMPTS.length)];
}

export default function () {
  const sessionId = `k6-chat-${__VU}-${__ITER}`;

  // Measure streaming/chat response
  const sendMessageQuery = `
    mutation SendMessage($input: SendMessageInput!) {
      sendMessage(input: $input) {
        id
        content
        role
        timestamp
      }
    }
  `;

  const variables = {
    input: {
      agentId: "default-agent",
      content: getRandomPrompt(),
      sessionId: sessionId,
    },
  };

  const payload = JSON.stringify({ query: sendMessageQuery, variables });

  const startTime = Date.now();
  const res = http.post(GRAPHQL_ENDPOINT, payload, {
    headers,
    tags: { name: "ChatMessage" },
    timeout: "30s",
  });
  const endTime = Date.now();

  const totalTime = endTime - startTime;
  totalResponseTime.add(totalTime);
  chatMessages.add(1);

  // For non-streaming responses, TTFT approximates the full response time.
  // For streaming endpoints, the initial chunk arrival time would be measured
  // separately via WebSocket or SSE handling.
  const ttft = res.timings.waiting;
  timeToFirstToken.add(ttft);

  const success = check(res, {
    "status is 200": (r) => r.status === 200,
    "response has data": (r) => {
      try {
        const body = r.json();
        return body.data && body.data.sendMessage;
      } catch {
        return false;
      }
    },
    "no GraphQL errors": (r) => {
      try {
        const body = r.json();
        return !body.errors || body.errors.length === 0;
      } catch {
        return false;
      }
    },
    "response time < 10s": (r) => r.timings.duration < 10000,
  });

  chatSuccess.add(success ? 1 : 0);

  // Simulate user reading the response before sending the next message
  sleep(Math.random() * 3 + 1);

  // Follow-up message in the same session
  const followUpVariables = {
    input: {
      agentId: "default-agent",
      content: "Can you elaborate on that?",
      sessionId: sessionId,
    },
  };

  const followUpPayload = JSON.stringify({
    query: sendMessageQuery,
    variables: followUpVariables,
  });

  const followUpRes = http.post(GRAPHQL_ENDPOINT, followUpPayload, {
    headers,
    tags: { name: "ChatFollowUp" },
    timeout: "30s",
  });

  const followUpTotalTime = Date.now() - (endTime + 1000);
  totalResponseTime.add(Math.max(followUpRes.timings.duration, 0));
  timeToFirstToken.add(followUpRes.timings.waiting);
  chatMessages.add(1);

  const followUpSuccess = check(followUpRes, {
    "follow-up status is 200": (r) => r.status === 200,
    "follow-up has data": (r) => {
      try {
        const body = r.json();
        return body.data && body.data.sendMessage;
      } catch {
        return false;
      }
    },
  });

  chatSuccess.add(followUpSuccess ? 1 : 0);

  sleep(Math.random() * 2 + 1);
}

export function handleSummary(data) {
  return {
    stdout: textSummary(data, { indent: "  ", enableColors: true }),
    "results/k6-chat-summary.json": JSON.stringify(data, null, 2),
  };
}

import { textSummary } from "https://jslib.k6.io/k6-summary/0.1.0/index.js";
