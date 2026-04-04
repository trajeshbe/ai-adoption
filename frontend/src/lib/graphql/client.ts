"use client";

import { Client, cacheExchange, fetchExchange } from "urql";

const GRAPHQL_URL =
  process.env.NEXT_PUBLIC_GRAPHQL_URL || "http://localhost:8000/graphql";

export const client = new Client({
  url: GRAPHQL_URL,
  exchanges: [cacheExchange, fetchExchange],
});
