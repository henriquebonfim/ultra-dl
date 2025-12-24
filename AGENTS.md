# Agent Instructions & Guidelines

This document serves as a guide for AI Agents and Developers working on the UltraDL repository.

## Core Philosophy
-   **Quality First**: Prioritize clean, readable, and well-tested code.
-   **Consistency**: Adhere strictly to the established project structure (FSD for frontend, modular Flask for backend).
-   **Stability**: Ensure all tests pass before submitting changes.

## Project Structure Rules

### Frontend (`/frontend`)
**Architecture**: Feature-Sliced Design (FSD)
-   **Do not** create "utils" or "components" folders at the root of `src`.
-   **Do** place code in the appropriate slice:
    -   `shared/`: UI Kit, basic helpers.
    -   `entities/`: Business logic, domain models (e.g., `video`, `user`).
    -   `features/`: User interactions (e.g., `download-video`, `change-settings`).
    -   `widgets/`: Composition of features/entities (e.g., `Header`, `Footer`).
    -   `pages/`: Full page layouts.
-   **Strict Imports**: Access layers from top to bottom (`pages` -> `widgets` -> `features` -> `entities` -> `shared`). Avoid circular dependencies.

### Backend (`/backend`)
-   **Modular Design**: Keep logic separated by domain/resource.
-   **Service Layer**: Business logic should reside in services, not directly in route handlers.
-   **Types**: Use type hints for all Python functions.

## 🛠 Tech Stack & Conventions

### Frontend
-   **Runtime**: Bun
-   **Strict Mode**: TypeScript strict mode is enabled. No `any` unless absolutely necessary.
-   **Styling**: TailwindCSS with `shadcn/ui` components. Use `clsx` and `tailwind-merge` for class manipulation.
-   **State**: Use React Query for async data. Avoid global state stores (Redux/Zustand) unless managing complex UI state.

### Backend
-   **Runtime**: Python 3.10+
-   **Linter**: `flake8` / `black` compatible.
-   **Async**: Use Celery for any task taking > 0.5s.

## Verification Steps

Before declaring a task complete, run the following:

### Frontend
1.  **Type Check**: `bun tsc --noEmit`
2.  **Test**: `bun test`
3.  **Lint**: `bun run lint`

### Backend
1.  **Test**: `pytest`
2.  **Lint**: Check for obvious pep8 violations (or run formatter).

## Common Commands

```bash
# Start Frontend Dev
cd frontend && bun run dev

# Start Backend Dev
cd backend && python main.py

# Run Full Stack (Docker)
docker-compose up --build
```

## Changelog

-   When adding features, update `README.md` if user-facing.
-   When changing architecture, update `ARCHITECTURE.md`.
