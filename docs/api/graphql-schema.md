# GraphQL API Documentation

## Endpoint

```
POST /graphql
WS   /graphql  (subscriptions)
```

Authentication: Bearer token in the `Authorization` header.

---

## Types

### User

```graphql
type User {
  id: ID!
  email: String!
  displayName: String!
  createdAt: DateTime!
}
```

### Bot

```graphql
enum BotType {
  WEATHER
  QUIZ
  RAG
}

type Bot {
  id: ID!
  name: String!
  type: BotType!
  description: String!
  isActive: Boolean!
}
```

### Conversation

```graphql
type Conversation {
  id: ID!
  user: User!
  bot: Bot!
  messages: [Message!]!
  createdAt: DateTime!
  updatedAt: DateTime!
}
```

### Message

```graphql
enum MessageRole {
  USER
  ASSISTANT
  SYSTEM
  TOOL
}

type Message {
  id: ID!
  conversationId: ID!
  role: MessageRole!
  content: String!
  toolCalls: [ToolCall!]
  tokenCount: Int
  latencyMs: Int
  createdAt: DateTime!
}
```

### ToolCall

```graphql
type ToolCall {
  id: ID!
  name: String!
  arguments: JSON!
  result: JSON
  durationMs: Int
}
```

### Document

```graphql
type Document {
  id: ID!
  filename: String!
  mimeType: String!
  sizeBytes: Int!
  chunkCount: Int!
  status: DocumentStatus!
  uploadedBy: User!
  createdAt: DateTime!
}

enum DocumentStatus {
  UPLOADING
  PROCESSING
  READY
  FAILED
}
```

### ChatToken (for streaming)

```graphql
type ChatToken {
  conversationId: ID!
  messageId: ID!
  token: String!
  isComplete: Boolean!
  finishReason: String
}
```

---

## Queries

### me

Returns the authenticated user.

```graphql
query {
  me {
    id
    email
    displayName
  }
}
```

### bots

List all available bots.

```graphql
query {
  bots {
    id
    name
    type
    description
    isActive
  }
}
```

### conversation

Get a single conversation by ID with its messages.

```graphql
query($id: ID!) {
  conversation(id: $id) {
    id
    bot { name type }
    messages {
      id
      role
      content
      toolCalls { name result }
      createdAt
    }
  }
}
```

### conversations

List conversations for the authenticated user, with pagination.

```graphql
query($first: Int, $after: String) {
  conversations(first: $first, after: $after) {
    edges {
      node {
        id
        bot { name }
        updatedAt
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### documents

List uploaded documents with optional status filter.

```graphql
query($status: DocumentStatus) {
  documents(status: $status) {
    id
    filename
    chunkCount
    status
    createdAt
  }
}
```

### searchDocuments

Semantic search over document chunks.

```graphql
query($query: String!, $topK: Int) {
  searchDocuments(query: $query, topK: $topK) {
    document { id filename }
    chunkContent
    similarityScore
  }
}
```

---

## Mutations

### sendMessage

Send a message to a bot and receive a response (non-streaming).

```graphql
mutation($conversationId: ID!, $content: String!) {
  sendMessage(conversationId: $conversationId, content: $content) {
    id
    role
    content
    toolCalls { name arguments result durationMs }
    tokenCount
    latencyMs
  }
}
```

### createConversation

Start a new conversation with a specified bot.

```graphql
mutation($botId: ID!) {
  createConversation(botId: $botId) {
    id
    bot { name type }
    createdAt
  }
}
```

### deleteConversation

Delete a conversation and all its messages.

```graphql
mutation($id: ID!) {
  deleteConversation(id: $id)
}
```

Returns `Boolean!`.

### uploadDocument

Upload a document for RAG indexing.

```graphql
mutation($file: Upload!) {
  uploadDocument(file: $file) {
    id
    filename
    sizeBytes
    status
  }
}
```

Uses the [GraphQL multipart request spec](https://github.com/jaydenseric/graphql-multipart-request-spec).

### deleteDocument

Remove a document and its chunks from storage.

```graphql
mutation($id: ID!) {
  deleteDocument(id: $id)
}
```

Returns `Boolean!`.

---

## Subscriptions

### onChatToken

Stream tokens as the bot generates a response. Connect via WebSocket.

```graphql
subscription($conversationId: ID!) {
  onChatToken(conversationId: $conversationId) {
    conversationId
    messageId
    token
    isComplete
    finishReason
  }
}
```

### onDocumentStatus

Receive real-time updates as a document is processed.

```graphql
subscription($documentId: ID!) {
  onDocumentStatus(documentId: $documentId) {
    id
    status
    chunkCount
  }
}
```

---

## Error Handling

All errors follow the standard GraphQL error format:

```json
{
  "errors": [
    {
      "message": "Conversation not found",
      "extensions": {
        "code": "NOT_FOUND",
        "statusCode": 404
      },
      "path": ["conversation"]
    }
  ]
}
```

| Error Code | Meaning |
|---|---|
| `NOT_FOUND` | Requested resource does not exist |
| `UNAUTHORIZED` | Missing or invalid authentication token |
| `FORBIDDEN` | Authenticated but lacking permission |
| `RATE_LIMITED` | Too many requests, retry after cooldown |
| `LLM_UNAVAILABLE` | LLM runtime is down or overloaded |
| `VALIDATION_ERROR` | Invalid input parameters |
