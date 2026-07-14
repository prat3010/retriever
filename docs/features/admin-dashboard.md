# Admin Dashboard — Agent Guide

## Overview

The admin dashboard (`apps/web/`) is a Next.js 14 App Router application that consumes the Retriever M9 admin API. It provides a browser-based interface for platform management — no SQL or terminal needed.

**Purpose:** Onboard clients, manage tenants/users/API keys/config, test API endpoints, and monitor platform health.

---

## 1. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Framework | Next.js 14 (App Router) | Server rendering, file-based routing, middleware |
| UI | shadcn/ui + Tailwind CSS v4 | Radix primitives, utility-first CSS, dark mode |
| State / Server | TanStack Query v5 | Caching, mutations, automatic revalidation |
| Client State | Zustand (sessionStorage) | Admin key persistence across page loads |
| Forms | Native + shadcn inputs | React Hook Form + Zod deferred until forms grow complex |
| Tables | TanStack Table v8 | Deferred until pagination/sorting needed |
| Notifications | sonner (Toaster) | Lightweight toast library |

### Key Dependencies (package.json)

```json
"dependencies": {
  "@radix-ui/react-dialog": "^1.1.19",
  "@radix-ui/react-dropdown-menu": "^2.1.20",
  "@radix-ui/react-select": "^2.3.3",
  "@radix-ui/react-tabs": "^1.1.17",
  "@tanstack/react-query": "^5.101.2",
  "lucide-react": "^1.24.0",
  "next": "^14.1.0",
  "sonner": "^2.0.7",
  "zustand": "^5.0.14",
  "class-variance-authority": "^0.7.1",
  "tailwind-merge": "^3.6.0",
  "tailwindcss-animate": "^1.0.7"
}
```

---

## 2. Directory Structure

```
apps/web/src/
├── app/
│   ├── globals.css             # Tailwind v4 @theme + shadcn HSL variables
│   ├── layout.tsx              # Root layout: QueryProvider + Toaster
│   ├── login/
│   │   └── page.tsx            # Admin master key login form
│   └── (dashboard)/
│       ├── layout.tsx          # AppShell wrapper (sidebar + topbar)
│       ├── page.tsx            # Dashboard home (stats overview)
│       ├── onboard/
│       │   └── page.tsx        # Client onboarding wizard (3 steps)
│       ├── tenants/
│       │   ├── page.tsx        # Tenant list table + deactivate dialog
│       │   └── [id]/
│       │       ├── page.tsx    # Tenant detail tabs (overview, users, keys, config)
│       │       └── playground/
│       │           └── page.tsx # API endpoint test console
├── components/
│   ├── app-shell.tsx           # Sidebar + main content layout with ErrorBoundary
│   ├── sidebar.tsx             # Navigation sidebar with logout
│   ├── topbar.tsx              # Page title bar (accepts children for actions)
│   ├── error-boundary.tsx      # React error boundary component
│   ├── ui/                     # shadcn/ui components (button, card, table, dialog, etc.)
│   ├── tenant-overview.tsx     # Overview tab: tenant info + deactivate
│   ├── tenant-documents.tsx    # Documents tab: list documents per tenant
│   ├── tenant-users.tsx        # Users tab: list + create user
│   ├── tenant-api-keys.tsx     # API Keys tab: list + generate + revoke
│   ├── tenant-prompts.tsx      # Prompts tab: CRUD + preview prompt templates
│   ├── tenant-sandbox.tsx      # Sandbox tab: RAG chat via SSE
│   └── tenant-config.tsx       # Config tab: AI provider, retrieval, security forms
├── hooks/
│   ├── use-query-client.tsx    # TanStack Query provider component
│   ├── use-tenants.ts          # Tenants queries + mutations
│   ├── use-users.ts            # Users per-tenant queries + mutations
│   ├── use-api-keys.ts         # API key queries + mutations
│   └── use-config.ts           # Config get/update mutations
├── lib/
│   ├── api.ts                  # Fetch wrapper with X-Admin-Master-Key header
│   ├── dates.ts                # Date formatting utilities
│   └── utils.ts                # shadcn cn() utility
├── store/
│   └── auth.ts                 # Zustand auth store (sessionStorage)
└── middleware.ts               # Auth guard: redirects to /login if no cookie
```

---

## 3. Authentication Flow

```
1. User visits /login
2. Enters admin master key
3. Login page:
   a. Stores key in Zustand → sessionStorage("admin_key")
   b. Sets cookie: admin_key=<key> (for middleware)
   c. Router pushes to /
4. Middleware checks cookie on every server request:
   - Missing → redirect /login
   - Present → allow through
5. API calls read key from Zustand store, send as X-Admin-Master-Key header
6. Logout clears sessionStorage + cookie → redirect /login
```

### Middleware (`src/middleware.ts`)

```typescript
// Guards all routes except /login, /_next, /api
// Reads admin_key from cookie or x-admin-key header
```

### Auth Store (`src/store/auth.ts`)

```typescript
// Zustand store backed by sessionStorage
// setKey(key) → sessionStorage + exposes reactive state
// clearKey() → removes from sessionStorage
```

### API Client (`src/lib/api.ts`)

```typescript
// api.get<T>(path), api.post<T>(path, body), api.put<T>(path, body), api.delete<T>(path)
// Automatically injects X-Admin-Master-Key header from store
// On 401: clears auth + redirects to /login
// API_BASE = NEXT_PUBLIC_API_URL || "http://localhost:8000"
```

---

## 4. Existing Pages & Their Functionality

### Login (`/login`)
- Password input for admin master key
- Stores in sessionStorage + sets cookie
- Redirects to `/` on submit

### Dashboard (`/`)
- Stats cards: total tenants, active, suspended, tiers count
- Data from `GET /v1/admin/tenants`

### Onboard Client (`/onboard`)
- 3-step wizard: Tenant info → API Key → Credentials summary
- Step 1: name, tier, isolation_level → creates tenant via `POST /v1/tenants`
- Step 2: key name, role, expiry → creates key via `POST /v1/admin/tenants/{id}/api-keys`
- Step 3: shows API base URL, Tenant ID, API key (copy button), curl examples
- Links to tenant detail page

### Tenant List (`/tenants`)
- Table: name, status, tier, created date
- Deactivate dialog per row
- Data from `GET /v1/admin/tenants`

### Tenant Detail (`/tenants/[id]`)
- Tabs: Overview, Users, API Keys, Config
- Topbar has "API Playground" button
- Tab data loaded via individual hooks

### API Playground (`/tenants/[id]/playground`)
- Endpoint selector: documents, search, config, API keys, users
- Input fields for API key + User ID
- JSON body editor (for POST endpoints)
- Response viewer
- Calls the actual retriever API with provided credentials

---

## 5. Page Component Patterns

### Page Template

```typescript
"use client";

import { Topbar } from "@/components/topbar";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function MyPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-resource"],
    queryFn: () => api.get<MyType[]>("/v1/admin/my-resource"),
  });

  return (
    <div>
      <Topbar title="My Page" description="Optional description">
        <Button>Action</Button>
      </Topbar>
      <div className="p-6">...</div>
    </div>
  );
}
```

### Adding a New Tab to Tenant Detail

1. Create component in `src/components/tenant-*.tsx`
2. Import in `src/app/(dashboard)/tenants/[id]/page.tsx`
3. Add `TabsTrigger` + `TabsContent` in the tab list

### Hook Pattern

```typescript
export function useMyResource() {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["my-resource"],
    queryFn: () => api.get<MyType[]>("/v1/admin/my-resource"),
  });
}

export function useUpdateMyResource(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: MyPayload) =>
      api.put(`/v1/admin/my-resource/${id}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["my-resource"] });
      toast.success("Updated successfully");
    },
  });
}
```

---

## 6. API Contract (Admin Endpoints)

All admin endpoints require `X-Admin-Master-Key` header.

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/tenants` | Create tenant (`name`, `tier`, `isolation_level`) |
| `GET` | `/v1/admin/tenants` | List all tenants |
| `GET` | `/v1/admin/tenants/{tenantId}` | Get tenant detail |
| `DELETE` | `/v1/admin/tenants/{tenantId}` | Deactivate tenant |
| `GET` | `/v1/admin/tenants/{tenantId}/users` | List users in tenant |
| `POST` | `/v1/admin/tenants/{tenantId}/users` | Create user (`external_id`, `display_name`) |
| `GET` | `/v1/admin/tenants/{tenantId}/api-keys` | List API keys |
| `POST` | `/v1/admin/tenants/{tenantId}/api-keys` | Create API key (`name`, `role`, `expires_in_days`) |
| `DELETE` | `/v1/admin/tenants/{tenantId}/api-keys/{keyId}` | Revoke API key |
| `GET` | `/v1/admin/tenants/{tenantId}/config` | Get tenant config (secrets visible) |
| `PUT` | `/v1/admin/tenants/{tenantId}/config` | Update tenant config |
| `GET` | `/v1/config/global` | Get global config |
| `PUT` | `/v1/config/global` | Update global config |

For client-facing endpoints (used in playground and reference client):
| Method | Path | Description |
|---|---|---|
| `GET` | `/v1/tenants/{tenantId}/documents` | List documents (requires `X-API-Key` + `X-User-ID`) |
| `POST` | `/v1/tenants/{tenantId}/search` | Search documents (requires `X-API-Key` + `X-User-ID`) |
| `POST` | `/v1/tenants/{tenantId}/chat/sessions` | Create chat session |
| `POST` | `/v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages` | Send message + SSE stream |

---

## 7. How to Add a New Page

### Step 1: Create the route file

```
src/app/(dashboard)/my-new-page/page.tsx
```

### Step 2: Write the page

```typescript
"use client";

import { Topbar } from "@/components/topbar";
import { useAuthStore } from "@/store/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function MyNewPage() {
  const adminKey = useAuthStore((s) => s.adminKey);
  const router = useRouter();

  useEffect(() => { if (!adminKey) router.push("/login"); }, [adminKey, router]);
  if (!adminKey) return null;

  return (
    <div>
      <Topbar title="My New Page" description="Description" />
      <div className="p-6">...</div>
    </div>
  );
}
```

### Step 3: Add to sidebar navigation

Edit `src/components/sidebar.tsx` — add to `navItems` array.

### Step 4: Add hook if API calls needed

Create in `src/hooks/use-*.ts` following existing patterns.

---

## 8. How to Add a New Tenant Tab

1. Create component `src/components/tenant-<name>.tsx`
2. Accept `tenantId: string` prop
3. Use existing hooks or create new ones
4. Import in `src/app/(dashboard)/tenants/[id]/page.tsx`
5. Add `<TabsTrigger>` and `<TabsContent>` in the tabs block

---

## 9. Code Standards

- **All pages use `"use client"`** — the dashboard is entirely client-rendered
- **No page-level `metadata` exports** — they conflict with `"use client"`
- **Import `@/` path alias** for all internal imports
- **Use `cn()` utility** for conditional class names
- **Follow existing component API** (shadcn patterns, lucide icons)
- **Toast on mutations**: `toast.success("...")` or `toast.error("...")`
- **Date formatting**: `formatDate()` / `formatDateTime()` from `@/lib/dates`
- **Loading states**: use `<Skeleton>` from shadcn for loading content
- **Error handling**: wrap page content with `<ErrorBoundary>` (already done in AppShell)
- **Never hardcode API URLs** — use `API_BASE` from env or `process.env.NEXT_PUBLIC_API_URL`

---

## 10. Reference Client

Location: `apps/client-reference/`

A standalone Next.js app that demonstrates how to integrate with the Retriever API from a client frontend. It shows the `X-API-Key` + `X-User-ID` header pattern.

**Tabs:** Config, Chat, Search, Documents
**Port:** 3001 (dev)

---

## 11. Future Enhancement Areas

- **Pagination** — TanStack Table + cursor-based pagination for tenant/user/document lists
- **React Hook Form + Zod** — form validation for config forms, user creation
- **User profile management** — within-tenant user editing
- **Document viewer** — preview documents per tenant
- **Responsive sidebar** — collapse on mobile
