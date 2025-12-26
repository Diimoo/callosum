# Onyx Web Frontend

The Next.js web application for Onyx.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm run start
```

## Project Structure

```text
web/
├── src/
│   ├── app/           # Next.js App Router pages
│   ├── components/    # React components
│   ├── hooks/         # Custom React hooks
│   ├── lib/           # Utility libraries
│   └── icons/         # SVG icon components
├── lib/
│   └── opal/          # Opal component library
├── public/            # Static assets
├── tests/             # Test files and setup
├── tailwind.config.js # Tailwind CSS configuration
└── next.config.js     # Next.js configuration
```

## Development

### Scripts

```bash
npm run dev           # Start dev server
npm run build         # Production build
npm run lint          # Run ESLint
npm run format        # Format with Prettier
npm run test          # Run Jest tests
npm run test:watch    # Run tests in watch mode
npm run types:check   # TypeScript type checking
```

### Code Standards

See [STANDARDS.md](./STANDARDS.md) for detailed coding guidelines, including:

- Always use absolute imports with `@` prefix
- Prefer regular functions over arrow functions for components
- Extract prop types into interfaces
- Use `cn()` utility for class names
- Use components from `refresh-components/` directory
- Use icons only from `src/icons/` directory

### Testing

Tests are co-located with source files:

```text
src/app/auth/login/
├── EmailPasswordForm.tsx
└── EmailPasswordForm.test.tsx
```

See [tests/README.md](./tests/README.md) for testing guidelines.

## Opal Component Library

The `lib/opal/` directory contains the Opal component library. See [lib/opal/README.md](./lib/opal/README.md) for usage details.

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for full list):

- `NEXT_PUBLIC_*` - Client-side variables
- `INTERNAL_URL` - Backend API URL for server-side requests
- `WEB_DOMAIN` - Public domain for the web app

### Tailwind CSS

Custom themes are defined in `tailwind-themes/`. The color system is carefully designed for light/dark mode - avoid using `dark:` modifiers (see STANDARDS.md).

## Docker

Build the Docker image:

```bash
docker build -t onyx-web-server .
```

## E2E Testing

Playwright tests are configured in `playwright.config.ts`:

```bash
# Run E2E tests
npx playwright test
```
