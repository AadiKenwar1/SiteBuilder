import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { STATUSES, statusMeta } from "@/lib/status"

export function StatusSelect({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  const current = value || "New"
  return (
    <Select value={current} onValueChange={onChange}>
      <SelectTrigger className="h-8 w-[176px] bg-card font-medium">
        <span className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${statusMeta(current).dot}`} />
          <SelectValue />
        </span>
      </SelectTrigger>
      <SelectContent>
        {STATUSES.map((s) => (
          <SelectItem key={s} value={s}>
            <span className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${statusMeta(s).dot}`} />
              {s}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
