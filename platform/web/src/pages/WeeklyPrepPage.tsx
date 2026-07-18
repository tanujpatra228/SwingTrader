import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { RoutineList } from "@/components/RoutineList"
import { useRoutine, WEEKEND_ITEMS } from "@/lib/routine"

export function WeeklyPrepPage() {
  const { rowProps } = useRoutine()

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Weekly Prep</h1>
        <p className="text-muted-foreground text-sm">
          Weekend routine — build next week's watchlist before Monday.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Weekend checklist</CardTitle>
        </CardHeader>
        <CardContent>
          <RoutineList items={WEEKEND_ITEMS} rowProps={rowProps} />
        </CardContent>
      </Card>
    </div>
  )
}
