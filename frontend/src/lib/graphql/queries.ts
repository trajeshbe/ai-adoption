import { gql } from "urql";

export const LIST_AGENTS = gql`
  query ListAgents {
    agents {
      id
      name
      agentType
      instructions
      createdAt
    }
  }
`;

export const GET_AGENT = gql`
  query GetAgent($id: UUID!) {
    agent(agentId: $id) {
      id
      name
      agentType
      instructions
      createdAt
    }
  }
`;

export const LIST_DOCUMENTS = gql`
  query ListDocuments {
    documents {
      id
      filename
      contentType
      chunkCount
      createdAt
    }
  }
`;

export const LIST_CHAT_SESSIONS = gql`
  query ListChatSessions {
    chatSessions {
      id
      agentId
      createdAt
      messages {
        id
        role
        content
        costUsd
        latencyMs
        createdAt
      }
    }
  }
`;

export const GET_COST_SUMMARY = gql`
  query GetCostSummary($period: String!) {
    costSummary(period: $period) {
      totalCostUsd
      totalInferences
      avgCostPerInference
      period
    }
  }
`;

export const LIST_INFERENCE_COSTS = gql`
  query ListInferenceCosts($limit: Int!) {
    inferenceCosts(limit: $limit) {
      totalCostUsd
      promptTokens
      completionTokens
      model
    }
  }
`;
