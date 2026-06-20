// Server component: fetch the leads on the server and hand them to the client
// table as initial data. This removes the old hydrate → fetch /api/leads →
// middleware getUser → Supabase waterfall that ran on every dashboard load.
// Access is already gated by middleware.ts, so calling the service-role data
// layer directly here is safe.
import { listLeads } from "@/lib/crm.server"
import { DashboardClient } from "./DashboardClient"

// CRM data must be fresh on every visit; never statically cache this route.
export const dynamic = "force-dynamic"

export default async function Dashboard() {
  const leads = await listLeads()
  return <DashboardClient initialLeads={leads} />
}
