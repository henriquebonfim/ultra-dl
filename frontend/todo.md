# Frontend - Task Tracker

> **Purpose**: Frontend-specific tasks following Feature-Sliced Design (FSD). For cross-cutting tasks, see [../todo.md](../todo.md).

**Last Updated**: November 11, 2025
**Priority**: High = 🔴 | Medium = 🟡 | Low = 🟢

---

## 🔴 Priority 1: Documentation Compression ✅ COMPLETE

### REQ-FRONTEND-DOC-1: Compress AGENTS.md ✅

**The system shall** reduce frontend/AGENTS.md from 478 lines to maximum 300 lines.

**Tasks**:
- [x] ✅ Remove redundant component development patterns
- [x] ✅ Consolidate workflow sections
- [x] ✅ Extract verbose examples to separate files
- [x] ✅ Keep: Core patterns, FSD rules, testing guidelines
- [x] ✅ Update with FSD-specific agent workflows

**Target**: 300 lines max
**Original**: 478 lines
**Final**: 280 lines
**Reduction**: 198 lines (41.4%)

---

## 🔴 Priority 2: FSD Migration

### REQ-FRONTEND-FSD-1: Create FSD Structure

**WHEN** frontend architecture is modernized, **THEN** the system shall organize code using Feature-Sliced Design with 6 layers: app → pages → widgets → features → entities → shared.

**Phase 1: Create Structure** 🔴 HIGH PRIORITY

**Tasks**:
- [ ] Create layer directories:
  ```bash
  cd frontend/src
  mkdir -p app/{providers,router,styles}
  mkdir -p pages/{home,download}
  mkdir -p widgets/{video-download-form,download-progress,format-selector}
  mkdir -p features/{url-validation,format-selection,download-management,progress-tracking}
  mkdir -p entities/{video,job,format}
  mkdir -p shared/{ui,lib,api,config,hooks}
  ```

- [ ] Set up path aliases in `vite.config.ts`:
  ```typescript
  resolve: {
    alias: {
      '@/app': '/src/app',
      '@/pages': '/src/pages',
      '@/widgets': '/src/widgets',
      '@/features': '/src/features',
      '@/entities': '/src/entities',
      '@/shared': '/src/shared',
    }
  }
  ```

- [ ] Update `tsconfig.json` with path aliases:
  ```json
  {
    "compilerOptions": {
      "paths": {
        "@/app/*": ["./src/app/*"],
        "@/pages/*": ["./src/pages/*"],
        "@/widgets/*": ["./src/widgets/*"],
        "@/features/*": ["./src/features/*"],
        "@/entities/*": ["./src/entities/*"],
        "@/shared/*": ["./src/shared/*"]
      }
    }
  }
  ```

- [ ] Create README.md in each layer directory explaining purpose
- [ ] Document FSD import rules in architecture.md (DONE ✅)

**Status**: Structure planned, not yet created

---

### REQ-FRONTEND-FSD-2: Migrate Components

**Phase 2: Migrate Components** 🟡 MEDIUM PRIORITY

**Tasks**:

**Step 1: Migrate Shared UI**
- [ ] Move `src/components/ui/*` to `src/shared/ui/`
- [ ] Keep shadcn/ui components (button, card, input, etc.)
- [ ] Update imports across codebase

**Step 2: Create Feature Slices**
- [ ] Create `features/url-validation/`:
  ```
  features/url-validation/
  ├── index.ts                    # export { UrlInput, useUrlValidation }
  ├── ui/UrlInput.tsx            # Component
  ├── model/useUrlValidation.ts  # Hook
  └── types.ts                    # Types
  ```
  - [ ] Extract URL input logic from components/UrlInput.tsx
  - [ ] Create public API (index.ts)
  - [ ] Update imports

- [ ] Create `features/format-selection/`:
  ```
  features/format-selection/
  ├── index.ts
  ├── ui/FormatPicker.tsx
  ├── model/useFormatSelection.ts
  └── types.ts
  ```
  - [ ] Extract from components/ResolutionPicker.tsx
  - [ ] Create public API

- [ ] Create `features/download-management/`:
  ```
  features/download-management/
  ├── index.ts
  ├── ui/DownloadButton.tsx
  ├── model/useDownload.ts
  └── types.ts
  ```
  - [ ] Extract download logic
  - [ ] Create public API

- [ ] Create `features/progress-tracking/`:
  ```
  features/progress-tracking/
  ├── index.ts
  ├── ui/ProgressBar.tsx
  ├── model/useProgress.ts
  └── types.ts
  ```
  - [ ] Extract from components/ProgressTracker.tsx
  - [ ] Create public API

**Step 3: Create Entity Slices**
- [ ] Create `entities/video/`:
  ```
  entities/video/
  ├── index.ts
  ├── model/types.ts
  ├── api/
  │   ├── getVideoInfo.ts
  │   └── getFormats.ts
  └── lib/formatters.ts
  ```

- [ ] Create `entities/job/`:
  ```
  entities/job/
  ├── index.ts
  ├── model/types.ts
  ├── api/
  │   ├── createJob.ts
  │   ├── getJobStatus.ts
  │   └── deleteJob.ts
  └── lib/jobHelpers.ts
  ```

- [ ] Create `entities/format/`:
  ```
  entities/format/
  ├── index.ts
  ├── model/types.ts
  └── lib/formatHelpers.ts
  ```

**Step 4: Create Widget Compositions**
- [ ] Create `widgets/video-download-form/`:
  - [ ] Compose UrlInput + FormatPicker + DownloadButton
  - [ ] Add widget-level state management
  - [ ] Create public API

- [ ] Create `widgets/download-progress/`:
  - [ ] Compose ProgressBar + status display
  - [ ] Add polling/WebSocket logic
  - [ ] Create public API

**Step 5: Create Pages**
- [ ] Create `pages/home/`:
  - [ ] Compose VideoDownloadForm widget
  - [ ] Add page layout
  - [ ] Update router

- [ ] Create `pages/download/`:
  - [ ] Compose DownloadProgress widget
  - [ ] Add page layout
  - [ ] Update router

**Step 6: Migrate App Layer**
- [ ] Move providers to `app/providers/`
- [ ] Move router config to `app/router/`
- [ ] Move global styles to `app/styles/`
- [ ] Update main.tsx to use app layer

---

### REQ-FRONTEND-FSD-3: Migrate Business Logic

**Phase 3: Migrate Business Logic** 🟡 MEDIUM PRIORITY

**Tasks**:
- [ ] Extract hooks from components to feature model/ directories
- [ ] Move API calls to entities/
- [ ] Create shared utilities in shared/lib/
- [ ] Remove circular dependencies
- [ ] Verify layer isolation (no upward imports)

---

### REQ-FRONTEND-FSD-4: Update Tests

**Phase 4: Update Tests** 🟢 LOW PRIORITY

**Tasks**:
- [ ] Reorganize tests to match FSD structure:
  ```
  tests/
  ├── features/
  │   ├── url-validation.test.tsx
  │   ├── format-selection.test.tsx
  │   └── ...
  ├── entities/
  │   ├── video.test.ts
  │   └── job.test.ts
  ├── widgets/
  │   └── video-download-form.test.tsx
  └── integration/
      └── download-flow.test.tsx
  ```

- [ ] Update import paths in all tests
- [ ] Add feature isolation tests
- [ ] Verify 90% coverage maintained
- [ ] Add integration tests for full flows

---

## 🟡 Priority 3: Complete Existing Tests

### REQ-FRONTEND-TEST-1: Verify Test Completeness

**The system shall** complete or remove incomplete test files to maintain code quality.

**Tasks**:
- [ ] Review `components/ErrorCard.test.tsx` (164 lines)
  - [ ] Verify test coverage
  - [ ] Add missing test cases
  - [ ] Check assertions

- [ ] Review `components/ProgressTracker.test.tsx` (164 lines)
  - [ ] Verify test coverage
  - [ ] Add WebSocket tests
  - [ ] Add polling tests

- [ ] Review `components/ResolutionPicker.test.tsx` (164 lines)
  - [ ] Verify format selection logic
  - [ ] Add edge case tests
  - [ ] Test grouping logic

- [ ] Review `components/UrlInput.test.tsx` (164 lines)
  - [ ] Verify validation tests
  - [ ] Add error handling tests
  - [ ] Test debounce behavior

**Decision**: Complete vs Remove
- If tests cover >80% of component: Complete remaining tests
- If tests are placeholder/incomplete: Remove and rewrite during FSD migration

---

## 🟡 Priority 4: Rate Limit Counter

### REQ-FRONTEND-RATE-1: Display Rate Limit Counters

**The system shall** display remaining request counts in the client footer for each rate limit category.

**Tasks**:
- [ ] Create `features/rate-limit-display/`:
  ```
  features/rate-limit-display/
  ├── index.ts
  ├── ui/RateLimitCounter.tsx
  ├── model/useRateLimitStatus.ts
  └── types.ts
  ```

- [ ] Add rate limit counter to footer
- [ ] Fetch rate limit status from API
- [ ] Display for each category:
  - Video without audio (X/20 remaining)
  - Audio only (X/20 remaining)
  - Video + audio (X/20 remaining)
  - Total jobs (X/60 remaining)

- [ ] Update counter in real-time after each request
- [ ] Show warning when approaching limit (e.g., < 5 remaining)
- [ ] Show error when limit exceeded (HTTP 429)

---

## 🟡 Priority 5: Performance Optimization

### REQ-FRONTEND-PERF-1: Bundle Size Optimization

**The system shall** maintain frontend bundle size below 500KB (gzipped) for initial load.

**Tasks**:
- [ ] Install bundle analyzer: `npm install --save-dev rollup-plugin-visualizer`
- [ ] Add to vite.config.ts:
  ```typescript
  import { visualizer } from 'rollup-plugin-visualizer'

  export default defineConfig({
    plugins: [
      react(),
      visualizer({ open: true })
    ]
  })
  ```

- [ ] Run build and analyze: `npm run build`
- [ ] Identify large dependencies
- [ ] Implement code splitting:
  ```typescript
  const DownloadPage = lazy(() => import('@/pages/download'))
  ```

- [ ] Lazy load non-critical components
- [ ] Optimize shadcn/ui imports (tree shaking)
- [ ] Remove unused dependencies
- [ ] Configure chunk splitting in vite.config.ts

**Target**: < 500KB gzipped
**Measure**: Run `npm run build` and check dist/assets/ size

---

### REQ-FRONTEND-PERF-2: Render Performance

**Tasks**:
- [ ] Add React DevTools Profiler
- [ ] Identify slow components
- [ ] Memoize expensive calculations
- [ ] Use React.memo for pure components
- [ ] Optimize re-renders (useCallback, useMemo)
- [ ] Add virtual scrolling for long lists (if applicable)

---

## 🟢 Priority 6: UI/UX Enhancements

### REQ-FRONTEND-UX-1: Error Handling Improvements

**WHEN** errors occur, **THEN** the system shall provide user-friendly error messages with actionable guidance.

**Tasks**:
- [ ] Standardize error display component
- [ ] Add error recovery suggestions:
  - Invalid URL → "Please enter a valid YouTube URL"
  - Network error → "Check your connection and try again"
  - Rate limit → "You've reached the daily limit. Try again tomorrow."
- [ ] Add retry mechanism for transient errors
- [ ] Show loading states for all async operations
- [ ] Add success feedback (toasts)

---

### REQ-FRONTEND-UX-2: Accessibility (a11y)

**The system shall** meet WCAG 2.1 Level AA accessibility standards.

**Tasks**:
- [ ] Add proper ARIA labels
- [ ] Ensure keyboard navigation works
- [ ] Add focus management
- [ ] Ensure proper color contrast (check with axe DevTools)
- [ ] Add screen reader support
- [ ] Test with keyboard only
- [ ] Add skip navigation links

---

## 🟢 Priority 7: Testing Infrastructure

### REQ-FRONTEND-TEST-2: E2E Testing

**Tasks**:
- [ ] Set up Playwright or Cypress
- [ ] Write E2E tests for critical flows:
  - [ ] Download video flow
  - [ ] Error handling
  - [ ] Progress tracking
  - [ ] Rate limiting
- [ ] Add to CI/CD pipeline

---

### REQ-FRONTEND-TEST-3: Visual Regression Testing

**Tasks**:
- [ ] Set up Chromatic or Percy
- [ ] Capture component snapshots
- [ ] Add to CI/CD pipeline
- [ ] Review visual changes in PRs

---

## 📊 Progress Tracking

### Completed ✅
- [x] React 18 + TypeScript setup
- [x] Vite build configuration
- [x] TanStack Query integration
- [x] shadcn/ui component library
- [x] Tailwind CSS styling
- [x] Socket.IO client
- [x] Component tests (some complete)
- [x] architecture.md created with FSD documentation
- [x] AGENTS.md compression (478 → 280 lines, 41.4% reduction)

### In Progress ⚠️
- [ ] FSD migration (Phase 1: Structure)
- [ ] Test completion/verification (4 files)

### Blocked 🚫
- FSD Phase 2-4 (blocked by Phase 1 completion)

---

## 🔗 Related Documentation

- **[architecture.md](./architecture.md)** - Frontend FSD architecture
- **[AGENTS.md](./AGENTS.md)** - Frontend AI agent guidelines
- **[README.md](./README.md)** - Frontend service overview
- **[../todo.md](../todo.md)** - Root-level consolidated tasks
- **[../architecture.md](../architecture.md)** - System-wide architecture
