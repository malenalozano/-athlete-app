# athlete. — Web app

React SPA for [`athlete.`](../README.md). Vite + TypeScript + Tailwind, dark theme, mobile-first.

> The folder is named `Figma/` for historical reasons — the first screens were exported from a Figma design.
> It is the real, and only, frontend.

## Run it

```bash
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev        # http://localhost:5173
npm run build      # production bundle
```

## Layout

```
src/app/
├── pages/          One file per route (LandingPage, Diario, Calendario, PlanSemanal, Profile, …)
├── components/     Shared components; components/ui = shadcn/Radix primitives
├── context/        UserContext — active user, persisted in localStorage
├── api.ts          Every call to the API lives here. Components never call fetch directly.
└── routes.ts       React Router config; all routes except "/" are lazy-loaded
```

## Conventions

- **New API call** → add a typed function to `api.ts`, then use it in the component.
- **New route** → register it in `routes.ts` with `lazy: () => import(...)`, and add it to `Header.tsx` if it
  belongs in the navigation.
- **Theme** → dark only. Accent `#C9FF00`, background `#0E1117`, cards `#161B22`, secondary text `#8B949E`.
  Icons from `lucide-react`.

## Deployment

Vercel, project root `Figma/`. Pushes to `main` that touch `Figma/**` trigger
`.github/workflows/frontend-deploy.yml`.
