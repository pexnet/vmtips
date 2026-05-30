# VMTips Frontend

React + TypeScript + Vite frontend for the VMTips World Cup 2026 prediction app.

## Development

```bash
npm install
npm run dev
```

The development server defaults to `http://localhost:5173`.

## Checks

```bash
npm run lint
npm run build
```

## Key Files

- `src/pages/MatchesPage.tsx` - group-stage match predictions
- `src/pages/KnockoutPage.tsx` - knockout predictions
- `src/components/BracketViewTab.tsx` - predicted/actual bracket view
- `src/utils/standings.ts` - client-side FIFA group ranking preview
- `src/locales/` - Swedish and English UI text
