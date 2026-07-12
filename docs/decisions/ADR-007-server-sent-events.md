# ADR-007: Use Server-Sent Events for Real-Time Streaming Generation

## Status
Accepted

## Context
Retriever acts as a grounded generative platform. Chat queries process contexts through Large Language Models, which generate tokens sequentially. To ensure responsiveness, generated tokens and citation metadata must stream to the client in real time.

## Problem
Selecting a streaming mechanism requires balancing network complexity, latency, browser support, and ease of implementation:
1. Long-polling adds high network overhead and latency.
2. WebSockets supports bi-directional streaming but requires complex connection handshakes, custom framing protocols, and is harder to load-balance.
3. The stream must deliver distinct event types (e.g. text tokens, citation references, performance logs, and error status updates).

## Decision
Utilize **Server-Sent Events (SSE)** via HTTP for streaming generations to clients.

## Alternatives Considered
* **WebSockets:** WebSockets are ideal for bi-directional real-time applications (e.g. collaborative whiteboards), but Retriever's chat flow is request-response based (one prompt input, one streamed output), making WebSockets unnecessary.
* **HTTP Chunked Transfer Encoding (Raw Text Stream):** A simple text streaming method, but lacks standard formatting schemas to separate token text from structured metadata (such as citation lists and performance logs).

## Consequences
* **Native Browser Support:** SSE is supported natively by browsers via the `EventSource` interface, simplifying client integration.
* **Granular Messaging:** Supports distinct structured event types (`token`, `citations`, `done`, `error`) within the same stream.
* **Simplified Load Balancing:** SSE runs over standard HTTP, making it easy to route, load-balance, and trace through API Gateways.
* **Client Constraint:** SSE is uni-directional. Downstream clients send user inputs via standard POST requests, and receive responses over the SSE channel.
* **Operational Constraint:** Requires configuring servers (e.g., Gunicorn, Nginx) to disable response buffering, ensuring tokens flush immediately.

## Future Review Criteria
* Monitor concurrent connection limits. If client connection limits are hit, evaluate HTTP/2 configurations to allow connection multiplexing.
