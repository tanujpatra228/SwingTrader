import { useState } from "react"
import { AppSidebar, type Page } from "@/components/AppSidebar"
import { WeeklyPrepPage } from "@/pages/WeeklyPrepPage"
import { TradingDayPage } from "@/pages/TradingDayPage"

export function App() {
  const [page, setPage] = useState<Page>("trading")

  return (
    <div className="bg-background flex">
      <AppSidebar page={page} onNavigate={setPage} />
      <main className="min-w-0 flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-6xl">
          {page === "weekly" ? <WeeklyPrepPage /> : <TradingDayPage />}
        </div>
      </main>
    </div>
  )
}

export default App
