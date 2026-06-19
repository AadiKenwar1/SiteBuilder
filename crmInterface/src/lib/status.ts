// Canonical pipeline — kept in sync with scraper/pipeline/crm.py (_STATUS_FILL).
export const STATUSES = [
  "New",
  "Built",
  "Emailed",
  "Emailed + Called",
  "Won",
  "Lost",
] as const

export type Status = (typeof STATUSES)[number]

// Tailwind classes per status: a dot (for the dropdown) and a chip (for badges).
export const STATUS_META: Record<string, { dot: string; chip: string }> = {
  "New":              { dot: "bg-white ring-1 ring-inset ring-zinc-400", chip: "bg-zinc-100 text-zinc-700 border border-zinc-200" },
  "Built":            { dot: "bg-amber-400",  chip: "bg-amber-100 text-amber-900 border border-amber-200" },
  "Emailed":          { dot: "bg-sky-400",    chip: "bg-sky-100 text-sky-900 border border-sky-200" },
  "Emailed + Called": { dot: "bg-blue-600",   chip: "bg-blue-100 text-blue-900 border border-blue-200" },
  "Won":              { dot: "bg-green-600",  chip: "bg-green-100 text-green-900 border border-green-200" },
  "Lost":             { dot: "bg-red-600",    chip: "bg-red-100 text-red-900 border border-red-200" },
}

export function statusMeta(s: string) {
  return STATUS_META[s] ?? STATUS_META["New"]
}
