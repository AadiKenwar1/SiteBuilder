#!/usr/bin/env bash
#
# init-artifact.sh <project-name>
# Scaffold a React + TypeScript + Vite project preconfigured with Tailwind CSS
# 3.4.1, the shadcn/ui theming system + a core component set, path aliases (@/),
# react-router-dom, and Parcel-ready tsconfig paths.
#
set -euo pipefail

NAME="${1:-artifact}"
NPM_FLAGS="--no-fund --no-audit"

echo "==> Creating Vite React+TS project: $NAME"
npm create vite@latest "$NAME" -- --template react-ts
cd "$NAME"

# Pin Vite for older Node (Vite 6/7 need Node 20+).
NODE_MAJOR=$(node -p "process.versions.node.split('.')[0]")
if [ "$NODE_MAJOR" -lt 20 ]; then
  echo "==> Node $NODE_MAJOR detected; pinning Vite 5"
  npm install $NPM_FLAGS -D vite@5.4.10 @vitejs/plugin-react@4
fi

echo "==> Installing dependencies"
npm install $NPM_FLAGS
npm install $NPM_FLAGS react-router-dom
npm install $NPM_FLAGS class-variance-authority clsx tailwind-merge lucide-react
npm install $NPM_FLAGS -D tailwindcss@3.4.1 postcss autoprefixer tailwindcss-animate

# ── Tailwind config ───────────────────────────────────────────────────────────
cat > tailwind.config.js <<'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "2rem", screens: { "2xl": "1400px" } },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)" },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: { "accordion-down": "accordion-down 0.2s ease-out", "accordion-up": "accordion-up 0.2s ease-out" },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
EOF

cat > postcss.config.js <<'EOF'
export default { plugins: { tailwindcss: {}, autoprefixer: {} } }
EOF

# ── Global CSS with shadcn variables ─────────────────────────────────────────
cat > src/index.css <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }
  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * { @apply border-border; }
  body { @apply bg-background text-foreground; }
}
EOF

# ── cn() helper ───────────────────────────────────────────────────────────────
mkdir -p src/lib
cat > src/lib/utils.ts <<'EOF'
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
EOF

# ── shadcn config ─────────────────────────────────────────────────────────────
cat > components.json <<'EOF'
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": { "components": "@/components", "utils": "@/lib/utils" }
}
EOF

# ── Vite alias ────────────────────────────────────────────────────────────────
cat > vite.config.ts <<'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
})
EOF

# ── tsconfig path alias ───────────────────────────────────────────────────────
# Add to tsconfig.json (read by parcel-resolver-tspaths during bundling) AND
# tsconfig.app.json (what `tsc`/Vite type-check the app with).
node -e '
const fs = require("fs");
for (const f of ["tsconfig.json", "tsconfig.app.json"]) {
  if (!fs.existsSync(f)) continue;
  const j = JSON.parse(fs.readFileSync(f, "utf8"));
  j.compilerOptions = Object.assign({}, j.compilerOptions, { paths: { "@/*": ["./src/*"] } });
  fs.writeFileSync(f, JSON.stringify(j, null, 2));
}
'

# ── shadcn/ui components (best effort; scaffold succeeds even if some fail) ────
echo "==> Adding shadcn/ui components"
npx --yes shadcn@latest add button table badge select dropdown-menu dialog alert-dialog card input label sonner tooltip separator skeleton scroll-area --yes --overwrite || \
  echo "WARN: some shadcn components failed to add; add them later with 'npx shadcn@latest add <name>'"

echo ""
echo "==> Done. Project '$NAME' is ready."
echo "    Dev:    cd $NAME && npm run dev"
echo "    Bundle: bash ../skills/web-artifacts-builder/scripts/bundle-artifact.sh"
