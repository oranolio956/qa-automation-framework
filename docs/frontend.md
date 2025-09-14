# Frontend: Multi-Step Form UX & PWA

This document defines the multi-step onboarding experience, interaction patterns, validation strategy, offline behavior, and accessibility for a mobile-first PWA.

## Tech Stack

- React 18+ with TypeScript
- Next.js (App Router) for SSR/SSG and API routes
- React Hook Form + Zod for form state and schema validation
- Zustand or Redux Toolkit for global onboarding state
- Socket.io client for realtime updates
- Workbox for service worker and offline caching
- IndexedDB (Dexie) for local persistence

## Multi-Step Form Architecture

```ts
export interface FormField {
  id: string;
  name: string;
  label: string;
  type: 'text' | 'email' | 'phone' | 'select' | 'date' | 'file' | 'radio' | 'checkbox';
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
}

export interface FormStep {
  id: string;
  title: string;
  description: string;
  fields: FormField[];
  validation: unknown; // Zod schema
  canSkip: boolean;
  saveOnExit: boolean;
  dependencies?: string[];
}

export interface NavigationState {
  currentStep: number;
  completedSteps: Set<number>;
  validationErrors: Map<string, string[]>;
  unsavedChanges: boolean;
  progress: number;
}
```

### Navigation Patterns

- Linear default with optional non-linear step jump when dependencies met
- Keyboard, click, and swipe gestures on mobile
- Guard transitions with form-level validation; field-level validation on blur and change

### Validation Strategy

- Zod schemas per step; cross-step validation for dependent fields (e.g., license state -> license number format)
- Debounced async validators for uniqueness or provider checks
- Show inline, contextual errors, preserving progress and inputs

### Save & Resume

- Auto-save every 30 seconds and on step exit; store to IndexedDB and sync to server
- Manual Save button; optimistic UI with rollback on error
- Session recovery: hydrate state from IndexedDB if server is behind

### Offline & PWA

- Installable PWA with Workbox precache for shell and critical routes
- Background sync queue for saves and uploads; retries with exponential backoff
- IndexedDB storage for drafts, uploads, and pending mutations

### Document Upload UX

- Drag & drop on desktop; camera capture on mobile (input capture="environment")
- Show file preview, size/type checks, and per-file progress bars
- Chunked uploads with pause/resume; retry failed chunks
- Real-time status: processing, completed, failed via WebSocket

### Real-time Feedback

- Socket.io subscription per contractor to receive verification and badge events
- Visual affordances: toasts for status changes; checkmarks for completed steps

### Gamification

- Progress ring reflecting weighted completion; accelerate near the end (goal gradient)
- Badge shelf with locked/unlocked states and tooltips

### Accessibility (WCAG 2.1)

- Minimum 44×44px touch targets with 8px spacing
- Proper labels, aria-* attributes, described-by for errors
- Focus management on step change; visible focus rings
- Color contrast ≥ 4.5:1; supports prefers-reduced-motion

## Responsive Layout

```css
:root {
  --mobile: 320px;
  --tablet: 768px;
  --desktop: 1024px;
  --large: 1440px;
}

.form-container {
  padding: 1rem;
  max-width: 100%;
}

@media (min-width: 768px) {
  .form-container {
    padding: 2rem;
    max-width: 800px;
    margin: 0 auto;
  }
}

@media (min-width: 1024px) {
  .form-container {
    max-width: 1200px;
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 2rem;
  }
}
```

## Components

- Stepper: clickable steps with completed state
- ProgressRing: animated circular progress indicator
- FormField components: TextInput, Select, DatePicker, FileUpload, PhoneInput with masking
- SaveBar: sticky footer with Save/Next/Back and offline indicator
- UploadManager: handles chunking, retries, and resumable state

## Autosave & Sync Pseudocode

```ts
const AUTO_SAVE_MS = 30000;

useEffect(() => {
  const i = setInterval(() => {
    if (state.unsavedChanges) {
      saveDraftToIndexedDb(state);
      queueSyncToServer(state);
    }
  }, AUTO_SAVE_MS);
  return () => clearInterval(i);
}, [state.unsavedChanges]);
```

## Error Handling

- Preserve inputs on validation failure; scroll to first error
- Show retriable banners for network failures; keep working offline
- Central error boundary with Sentry logging

