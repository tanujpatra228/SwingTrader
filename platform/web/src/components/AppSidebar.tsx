import { CalendarDays, LineChart, TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"

export type Page = "weekly" | "trading"

const NAV: { id: Page; label: string; hint: string; icon: typeof CalendarDays }[] = [
  { id: "weekly", label: "Weekly Prep", hint: "Weekend routine", icon: CalendarDays },
  { id: "trading", label: "Trading Day", hint: "Evening routine", icon: LineChart },
]

export function AppSidebar({ page, onNavigate }: { page: Page; onNavigate: (p: Page) => void }) {
  return (
    <aside className="bg-sidebar text-sidebar-foreground border-sidebar-border flex h-screen w-60 shrink-0 flex-col border-r">
      <div className="flex items-center gap-2 px-4 py-4">
        <TrendingUp className="text-sidebar-primary size-5" />
        <span className="font-semibold tracking-tight">Swing Trader</span>
      </div>

      <nav className="flex-1 space-y-1 px-2">
        {NAV.map((item) => {
          const Icon = item.icon
          const active = page === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
              )}
            >
              <Icon className="size-4 shrink-0" />
              <span className="flex flex-col">
                <span>{item.label}</span>
                <span className="text-sidebar-foreground/50 text-xs font-normal">{item.hint}</span>
              </span>
            </button>
          )
        })}
      </nav>

      <div className="text-sidebar-foreground/40 border-sidebar-border border-t px-4 py-3 text-xs">
        Not financial advice.
      </div>
    </aside>
  )
}
