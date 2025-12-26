# Onyx Chat Widget Example

A minimal example demonstrating how to embed an Onyx chat widget in a Next.js application.

## Overview

This example shows how to integrate with the Onyx chat API to create a streaming chat interface. It demonstrates:

- Creating chat sessions via the Onyx API
- Sending messages and handling streaming responses
- Parsing chunked JSON responses
- Rendering markdown in chat messages

## Prerequisites

- Node.js 18+
- An Onyx instance (cloud or self-hosted)
- An Onyx API key

## Setup

1. Install dependencies:

```bash
npm install
```

2. Configure environment variables:

```bash
cp .env.example .env
```

Edit `.env` with your Onyx instance details:

```
NEXT_PUBLIC_API_URL=https://your-onyx-instance.com
NEXT_PUBLIC_API_KEY=your_api_key_here
```

3. Start the development server:

```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000)

## Project Structure

```
examples/widget/
├── src/
│   └── app/
│       ├── page.tsx           # Main page with widget
│       ├── layout.tsx         # App layout
│       ├── globals.css        # Global styles
│       └── widget/
│           └── Widget.tsx     # Chat widget component
├── .env.example               # Environment template
├── package.json
└── README.md
```

## Key Features

### Streaming Responses

The widget handles streaming responses from the Onyx API, processing chunked JSON data in real-time:

```typescript
async function* handleStream<T>(streamingResponse: Response) {
  const reader = streamingResponse.body?.getReader();
  // Process chunks as they arrive
}
```

### API Integration

The widget integrates with these Onyx API endpoints:

- `POST /chat/create-chat-session` - Create a new chat session
- `POST /chat/send-message` - Send messages and receive streaming responses

## Customization

The widget component in `src/app/widget/Widget.tsx` can be customized to match your application's design. Key areas to modify:

- Styling via Tailwind CSS classes
- Message rendering and formatting
- Error handling and loading states

## Learn More

- [Onyx Documentation](https://docs.onyx.app)
- [Onyx API Reference](https://docs.onyx.app/apis)
