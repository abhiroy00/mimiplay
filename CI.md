# Continuous Integration (CI) — MimiPlay

CI runs automatically on every push and pull request to `main` or `develop`.
It catches broken code **before** it ever reaches a server.

---

## What CI Does

| Trigger | Frontend CI | Backend CI |
|---------|-------------|------------|
| Push to `main` or `develop` | Lint + Build | Python syntax check |
| Pull Request to `main` or `develop` | Lint + Build | Python syntax check |
| Deploy | Only after CI passes | Only after CI passes |

---

## Workflows

### 1. Frontend CI — `.github/workflows/frontend.yml`

**Runs when:** any file inside `frontend/` changes, or the workflow file itself changes.

**Steps in order:**

```
Checkout code
  ↓
Setup Node.js 20
  ↓
npm ci  (install exact versions from package-lock.json)
  ↓
npm run lint  (ESLint — must pass with zero errors)
  ↓
npm run build  (Vite build with VITE_API_URL injected from GitHub Secrets)
```

**What ESLint checks:**
- `no-unused-vars` — all imported variables must be used
- `no-empty` — no empty catch blocks (use `catch` without a variable instead)
- `react-hooks/rules-of-hooks` — hooks called correctly
- `react-hooks/exhaustive-deps` — useEffect dependency arrays complete
- `react-refresh/only-export-components` — hot-reload compatibility

**Key ESLint rule for Framer Motion:**
ESLint 9 does not recognise `<motion.div>` as a usage of `motion`. Fix: always import as uppercase alias so it is ignored by `varsIgnorePattern`:
```js
// WRONG - ESLint flags motion as unused
import { motion } from 'framer-motion'
<motion.div>...</motion.div>

// CORRECT - uppercase matches varsIgnorePattern '^[A-Z_]'
import { motion as Motion } from 'framer-motion'
<Motion.div>...</Motion.div>
```

**Vite environment variable rule:**
`VITE_` prefix is required for any env var that the React app can read at runtime. Variables are baked into the JS bundle at build time — they are NOT available at runtime like Node.js `process.env`.

```js
// frontend/src/config.js
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
//                                                         ↑ always add a fallback
```

If `VITE_API_URL` is not set during build, it compiles to `undefined` and every API call becomes `undefined/api/login` — causing a JSON parse error on the login page.

**How to run lint locally:**
```bash
cd frontend
npm ci
npm run lint
```

**How to run build locally:**
```bash
cd frontend
VITE_API_URL=http://localhost:5000 npm run build
```

---

### 2. Backend CI — `.github/workflows/backend.yml`

**Runs when:** any file inside `backend/` or `monitoring/` changes.

**Steps in order:**
```
Checkout code
  ↓
Setup Python 3.11
  ↓
python -m py_compile app.py config.py extensions.py mimi_llm_session.py
  (checks syntax only — no imports, no runtime needed)
```

**Why only syntax check?**
The backend has heavy dependencies (OpenAI, MongoDB, Redis, PostgreSQL, Qdrant). Installing all of them on a CI runner just to run tests is slow and expensive. A syntax check catches the most common errors (typos, bad indentation, missing colons) without needing any services running.

**How to run locally:**
```bash
cd backend
python -m py_compile app.py config.py extensions.py mimi_llm_session.py
echo "Syntax OK"
```

---

### 3. Monitoring CI — `.github/workflows/monitoring.yml`

**Runs when:** any file inside `monitoring/` changes (Prometheus or Grafana configs).

There is no separate CI job for monitoring — the workflow goes straight to reload. The config files (`.yml`, `.json`) are validated implicitly when Prometheus loads them on the EC2 server.

---

## GitHub Actions — Key Concepts Used

### Secrets pre-check pattern
GitHub Actions cannot use secrets in `if:` conditions directly (they evaluate to empty string, not `false`). The workaround:

```yaml
- name: Check secrets
  id: my_check
  env:
    MY_SECRET: ${{ secrets.MY_SECRET }}   # read into env var
  run: |
    if [ -z "$MY_SECRET" ]; then
      echo "skip=true" >> $GITHUB_OUTPUT   # set output flag
    else
      echo "skip=false" >> $GITHUB_OUTPUT
    fi

- name: Use secret
  if: steps.my_check.outputs.skip != 'true'   # gate on the flag
  ...
```

This pattern is used in all three workflows so CI/CD passes gracefully when secrets are not yet configured (e.g. staging EC2 not set up yet).

### GitHub Actions annotation limit
GitHub Actions UI shows a maximum of **10 error annotations** even if there are 100+ errors. Always run `npm run lint` locally to see the full list.

### react-hooks v7 new rules
`eslint-plugin-react-hooks` v7 added 13 React Compiler rules that default to `error`. Since MimiPlay does not use the React Compiler, all 13 are downgraded to `warn` in `eslint.config.js`:

```js
'react-hooks/static-components': 'warn',
'react-hooks/use-memo': 'warn',
'react-hooks/component-hook-factories': 'warn',
// ... (13 rules total)
```

---

## Branch Strategy

| Branch | Environment | CI runs | Deploy runs |
|--------|-------------|---------|-------------|
| `main` | Production | Yes | Yes (on push) |
| `develop` | Staging | Yes | Yes (on push) |
| Any PR | — | Yes | No |

CI must pass before the deploy job runs (`needs: ci`).

---

## Common CI Failures and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `motion is defined but never used` | ESLint 9 doesn't track JSX member usage | Rename `import { motion }` to `import { motion as Motion }` |
| `err is defined but never used` | ESLint 9 defaults caughtErrors to "all" | Change `catch (err)` to `catch` (ES2019+ optional catch binding) |
| `module is not defined` in tailwind.config.js | CJS file in ESM project | Add `tailwind.config.js` to `globalIgnores` in eslint.config.js |
| `react-hooks/static-components` error | react-hooks v7 React Compiler rules | Downgrade all 13 to `warn` in eslint.config.js |
| `Input required and not supplied: aws-region` | AWS secret is empty string, not undefined | Use env-var pre-check pattern (see above) |
| Vite build compiles `undefined` into bundle | `VITE_API_URL` secret not set | Add `|| 'http://localhost:5000'` fallback in config.js |
