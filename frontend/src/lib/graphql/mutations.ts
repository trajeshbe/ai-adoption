import { gql } from "urql";

export const CREATE_AGENT = gql`
  mutation CreateAgent($input: CreateAgentInput!) {
    createAgent(input: $input) {
      id
      name
      agentType
      instructions
      createdAt
    }
  }
`;

export const DELETE_AGENT = gql`
  mutation DeleteAgent($agentId: UUID!) {
    deleteAgent(agentId: $agentId)
  }
`;

export const SEND_MESSAGE = gql`
  mutation SendMessage($input: SendMessageInput!) {
    sendMessage(input: $input) {
      id
      role
      content
      costUsd
      latencyMs
      createdAt
    }
  }
`;

export const UPLOAD_DOCUMENT = gql`
  mutation UploadDocument($filename: String!, $contentType: String!) {
    uploadDocument(filename: $filename, contentType: $contentType) {
      id
      filename
      contentType
      chunkCount
      createdAt
    }
  }
`;
