# Frontend - React + TypeScript

Modern React frontend with TypeScript, Vite, and Tailwind CSS.

## Architecture

Component-based React architecture with feature-driven organization:

```
frontend/src/
├── components/          # React components
│   ├── ui/              # shadcn/ui components (10 components)
│   ├── UrlInput.tsx     # YouTube URL input
│   ├── VideoPreview.tsx # Video thumbnail and metadata
│   ├── ResolutionPicker.tsx # Format selection
│   ├── DownloadButton.tsx   # Download trigger
│   ├── ProgressTracker.tsx  # Progress display
│   ├── ErrorCard.tsx    # Error display
│   ├── Header.tsx       # App header
│   ├── Footer.tsx       # App footer
│   └── AdBanner.tsx     # Ad placeholder
├── hooks/               # Custom React hooks
│   ├── use-mobile.tsx   # Mobile detection
│   ├── use-toast.ts     # Toast notifications
│   └── useJobStatusWithWebSocket.ts # Job status tracking
├── lib/                 # Utilities
│   ├── utils.ts         # Tailwind helpers
│   └── errors.ts        # Error handling
├── pages/               # Route pages
│   ├── Index.tsx        # Main page
│   └── NotFound.tsx     # 404 page
├── App.tsx              # Root component
├── main.tsx             # Entry point
└── index.css            # Global styles
```

## Tech Stack

- **React 18.3.1** - UI library
- **TypeScript 5.9.3** - Type safety
- **Vite 5.4.21** - Build tool
- **Tailwind CSS 3.4.18** - Styling
- **TanStack Query 5.90.7** - Server state
- **Framer Motion 12.23.24** - Animations
- **Socket.IO Client 4.8.1** - WebSocket
- **Sonner 1.7.4** - Toast notifications
- **Lucide React 0.462.0** - Icons

## Dependencies (18 packages)

All packages are actively used:

**Core:**
- `react` + `react-dom` - UI library
- `react-router-dom` - Routing
- `@tanstack/react-query` - Server state management

**UI Components (4 Radix UI):**
- `@radix-ui/react-progress` - Progress bar
- `@radix-ui/react-slot` - Component composition
- `@radix-ui/react-toast` - Toast notifications
- `@radix-ui/react-tooltip` - Tooltips

**Styling:**
- `tailwindcss` + `autoprefixer` + `postcss` - CSS framework
- `tailwind-merge` - Class merging
- `tailwindcss-animate` - Animations
- `class-variance-authority` - Variant styling
- `clsx` - Class names utility
- `next-themes` - Theme support

**Features:**
- `framer-motion` - Animations
- `lucide-react` - Icons
- `socket.io-client` - Real-time updates
- `sonner` - Toast notifications

## UI Components (10 components)

Only actively used shadcn/ui components:

- `alert.tsx` - Alert messages
- `button.tsx` - Buttons
- `card.tsx` - Card containers
- `input.tsx` - Text inputs
- `progress.tsx` - Progress bars
- `sonner.tsx` - Toast notifications
- `toast.tsx` - Toast component
- `toaster.tsx` - Toast container
- `tooltip.tsx` - Tooltips
- `use-toast.ts` - Toast hook

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL |

## Development

### Run without Docker

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Access at http://localhost:5000
```

### Run with Docker

```bash
# Start frontend only
docker-compose up frontend

# Access at http://localhost:5000
```

## Build

```bash
# Production build
npm run build

# Preview production build
npm run preview

# Development build
npm run build:dev
```

**Build output:** `dist/` directory

## Testing

```bash
# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests once (CI)
npm run test:run
```

**Test files:**
- `src/components/UrlInput.test.tsx`
- `src/components/ResolutionPicker.test.tsx`
- `src/components/ProgressTracker.test.tsx`
- `src/components/ErrorCard.test.tsx`

## Linting

```bash
# Run ESLint
npm run lint
```

## Project Features

### URL Input Component
- YouTube URL validation
- Client-side validation
- API integration
- Loading states
- Error handling

### Video Preview Component
- Video thumbnail display
- Metadata (title, channel, duration)
- YouTube embed support
- Responsive design

### Resolution Picker Component
- Format grouping (Video+Audio, Video Only, Audio Only)
- Resolution sorting
- Quality labels
- Codec information
- Filesize display
- Compatibility notes

### Download Button Component
- Job creation
- Progress tracking
- WebSocket support
- Polling fallback

### Progress Tracker Component
- Real-time progress updates
- Status display (pending, processing, completed, failed)
- Download speed and ETA
- Expiration countdown
- Cancel/delete actions
- Video metadata display

### Error Handling
- Centralized error parsing
- User-friendly messages
- Actionable guidance
- Toast notifications
- Error categories

## Custom Hooks

### useJobStatusWithWebSocket
- WebSocket connection with polling fallback
- Automatic reconnection
- Job status tracking
- Progress updates
- Error handling

### use-mobile
- Mobile device detection
- Responsive breakpoints

### use-toast
- Toast notification management
- Multiple toast support

## Styling

**Tailwind CSS** with custom configuration:

- Dark theme (primary)
- Custom color system (HSL)
- CSS variables for theming
- Responsive breakpoints
- Custom animations
- Gradient utilities

**Key classes:**
- `gradient-primary` - Primary gradient
- `shadow-glow` - Glow effect
- `bg-card` - Card background
- `text-muted-foreground` - Muted text

## Path Aliases

`@/` maps to `./src/` for clean imports:

```typescript
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
```

## Troubleshooting

### Build Issues

```bash
# Clear cache and rebuild
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Type Errors

```bash
# Check TypeScript errors
npx tsc --noEmit
```

### Linting Issues

```bash
# Fix auto-fixable issues
npm run lint -- --fix
```

### WebSocket Connection Issues

Check backend WebSocket configuration:
- Ensure `SOCKETIO_ENABLED=true`
- Check CORS settings
- Verify backend is running

### API Connection Issues

Check `VITE_API_URL` environment variable:
```bash
echo $VITE_API_URL
```

## Performance

**Build time:** ~3.12s
**Bundle size:** ~783 KB (238 KB gzipped)
**Dependencies:** 18 packages (56% reduction from original)

## Performance Monitoring

### Running Performance Tests

**Build and Measure Bundle Size:**

```bash
# Production build via Docker
docker-compose exec frontend npm run build

# View build output (includes gzipped sizes)
# Look for total JS bundle size in output

# Expected output:
# dist/assets/react-vendor-*.js    ~107 KB gzipped
# dist/assets/ui-vendor-*.js        ~79 KB gzipped
# dist/assets/index-*.js            ~27 KB gzipped
# dist/assets/socket-vendor-*.js    ~13 KB gzipped
# dist/assets/query-vendor-*.js     ~12 KB gzipped
# Total: ~239 KB gzipped (target: <500KB)
```

**Verify Bundle Size Target:**

```bash
# Run bundle size test
docker-compose exec frontend npm run test:run -- tests/bundle-size.test.ts

# Should pass if total gzipped size <500KB
```

### Analyzing Bundle Composition

**Generate Bundle Visualizer:**

```bash
# Build and generate stats.html
docker-compose exec frontend npm run build

# View bundle visualizer (if configured)
docker-compose exec frontend npm run analyze

# Or manually open dist/stats.html in browser
```

**Bundle Visualizer Shows:**
- Chunk sizes (gzipped and uncompressed)
- Module composition within each chunk
- Dependency tree visualization
- Largest dependencies
- Optimization opportunities

**What to Look For:**
- Vendor chunks properly separated
- Application code in separate chunk
- No duplicate dependencies
- Tree shaking working correctly
- Large dependencies identified

### Profiling Component Performance

**Using React DevTools Profiler:**

1. Install React DevTools browser extension
2. Open application in browser
3. Open DevTools → Profiler tab
4. Click "Record" button
5. Interact with application
6. Stop recording and analyze results

**What to Look For:**
- Components rendering >16ms (60fps threshold)
- Unnecessary re-renders
- Components not using React.memo
- Expensive calculations not memoized
- Event handlers causing re-renders

**Optimized Components:**
- ResolutionPicker: Should not re-render with same props
- ProgressTracker: Should use useMemo for calculations
- VideoPreview: Should be memoized
- DownloadButton: Should use useCallback for handlers

### Running Component Performance Tests

**Test Memoization:**

```bash
# Run performance tests
docker-compose exec frontend npm run test:run -- tests/performance/

# Tests verify:
# - React.memo prevents unnecessary re-renders
# - useMemo prevents recalculation
# - useCallback maintains referential equality
```

### Monitoring Build Performance

**Track Build Times:**

```bash
# Measure build time
time docker-compose exec frontend npm run build

# Expected: ~3-4 seconds
# If slower, investigate:
# - Large dependencies added
# - Complex transformations
# - Slow file system (Docker volume)
```

**Build Optimization Tips:**
- Use Docker BuildKit for faster builds
- Cache node_modules in Docker volume
- Minimize file system operations
- Use production mode for final builds

### Interpreting Performance Metrics

**Bundle Size Metrics:**
- **Total JS (gzipped):** 239.47 KB ✅ (target: <500KB)
- **Build time:** 3.35s ✅
- **Chunks:** 5 optimized chunks ✅
- **Vendor separation:** Yes ✅

**Component Performance:**
- **Render time:** <16ms per component ✅
- **Re-renders:** Minimized with React.memo ✅
- **Calculations:** Memoized with useMemo ✅
- **Event handlers:** Stable with useCallback ✅

### Troubleshooting Performance Issues

**Large Bundle Size:**
1. Run bundle visualizer to identify large dependencies
2. Check for duplicate dependencies (use npm dedupe)
3. Verify tree shaking is working
4. Consider lazy loading for heavy components
5. Remove unused dependencies

**Slow Component Renders:**
1. Profile with React DevTools
2. Check for missing React.memo
3. Verify useMemo dependencies are correct
4. Look for expensive calculations in render
5. Check for unnecessary state updates

**Slow Build Times:**
1. Check Docker volume performance
2. Verify node_modules is cached
3. Look for large dependencies
4. Consider using esbuild for faster builds
5. Check for slow transformations

### Continuous Monitoring

**Set Up Checks:**
- Bundle size test in CI/CD pipeline
- Fail build if >500KB gzipped
- Monitor build times in CI/CD
- Track bundle size over time

**Regular Reviews:**
- Weekly: Check bundle size after new features
- Monthly: Profile components for performance
- Quarterly: Audit dependencies and remove unused

**Performance Baseline:**
- See [BASELINE_METRICS.md](./BASELINE_METRICS.md) for detailed metrics
- Compare new builds to baseline
- Track performance trends over time

### Performance Best Practices

**When Adding Features:**
1. Check bundle size impact after adding dependencies
2. Use React.memo for pure components
3. Apply useMemo for calculations >10ms
4. Use useCallback for handlers passed to children
5. Consider lazy loading for heavy components

**Before Deployment:**
1. Run production build and check bundle size
2. Profile components with React DevTools
3. Run performance tests
4. Verify all optimizations are working
5. Compare to baseline metrics

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)
