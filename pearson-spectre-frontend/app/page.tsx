"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { StatCard, Button } from "@/components/ui-components"
import { RecentWorkflows } from "@/components/recent-workflows"
import { LiveActivity } from "@/components/live-activity"
import { getDashboardStats, DashboardStats } from "@/lib/api-client"

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      const res = await getDashboardStats()
      if (res.data) setStats(res.data)
      setLoading(false)
    }
    load()
    // Refresh every 30s
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <TopBar
          title="Dashboard"
          subtitle={`Autonomous contract intelligence${stats ? ` · ${stats.active_workflows} workflows active` : ''}`}
          action={
            <Link href="/upload">
              <Button>New Analysis</Button>
            </Link>
          }
        />

        {/* Stat Cards */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          <StatCard
            label="Contracts Analyzed"
            value={loading ? "—" : stats?.contracts_analysed ?? 0}
            subtext={loading ? "Loading..." : `${stats?.total_contracts ?? 0} total uploaded`}
            subtextColor="green"
          />
          <StatCard
            label="Violations Detected"
            value={loading ? "—" : stats?.violation_count ?? 0}
            subtext={`${stats?.open_findings ?? 0} total findings`}
          />
          <StatCard
            label="Active Workflows"
            value={loading ? "—" : stats?.active_workflows ?? 0}
            subtext="running now"
            subtextColor="purple"
            showDot
          />
          <StatCard
            label="High Severity"
            value={loading ? "—" : stats?.high_severity_count ?? 0}
            subtext="findings flagged"
            subtextColor="amber"
          />
          <StatCard
            label="Avg Confidence"
            value={loading ? "—" : `${((stats?.avg_confidence ?? 0) * 100).toFixed(0)}%`}
            subtext="model accuracy"
            subtextColor="amber"
          />
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-[65fr_35fr] gap-6">
          <RecentWorkflows />
          <LiveActivity />
        </div>
      </main>
    </div>
  )
}
