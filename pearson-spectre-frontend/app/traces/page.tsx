"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { GlassCard, Badge, Button } from "@/components/ui-components"
import { getOmiumDashboard, getWorkflows, getWorkflowTasks, WorkflowRun, AgentTask, OmiumDashboard } from "@/lib/api-client"
import { ExternalLink } from "lucide-react"

function timeAgo(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default function TracesPage() {
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([])
  const [tasks, setTasks] = useState<Record<string, AgentTask[]>>({})
  const [omium, setOmium] = useState<OmiumDashboard | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      const wfRes = await getWorkflows()
      const omiumRes = await getOmiumDashboard()
      if (omiumRes.data) setOmium(omiumRes.data)
      if (wfRes.data) {
        setWorkflows(wfRes.data)
        // Load tasks for each workflow
        wfRes.data.forEach(async (wf) => {
          const tRes = await getWorkflowTasks(wf.id)
          if (tRes.data) {
            setTasks(prev => ({ ...prev, [wf.id]: tRes.data! }))
          }
        })
      }
      setLoading(false)
    }
    load()
  }, [])

  const getStatusBadge = (status: string) => {
    if (status === 'completed') return 'complete'
    if (status === 'running' || status === 'queued') return 'running'
    if (status === 'failed') return 'violation'
    return 'running'
  }

  // Compute aggregate stats from workflows
  const totalRuns = workflows.length
  const completedRuns = workflows.filter(w => w.status === 'completed').length
  const avgRuntime = workflows
    .filter(w => w.runtime_ms != null)
    .reduce((sum, w, _, arr) => sum + (w.runtime_ms! / arr.length), 0)

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <TopBar
          title="Trace Monitoring"
          subtitle="LangGraph pipeline traces and agent observability"
          action={
            <a href={omium?.dashboard_url ?? "https://www.omium.ai/"} target="_blank" rel="noopener noreferrer">
              <Button className="flex items-center gap-2">
                Open Omium.ai <ExternalLink className="w-3 h-3" />
              </Button>
            </a>
          }
        />

        <div className="mb-4 rounded-lg border border-[rgba(139,92,246,0.25)] bg-[rgba(139,92,246,0.08)] px-4 py-3 text-[12px] text-[#C4B5FD]">
          Omium project: <span className="font-mono">{omium?.project_id ?? "spectre"}</span>
          {" · "}
          Mode: <span className="font-mono">{omium?.mode ?? "local-trace-export"}</span>
          {" · "}
          Local trace export is available even when hosted Omium ingestion is disabled.
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total Runs", value: totalRuns },
            { label: "Completed", value: completedRuns },
            { label: "Avg Runtime", value: avgRuntime > 0 ? `${Math.round(avgRuntime)}ms` : "—" },
            { label: "Success Rate", value: totalRuns > 0 ? `${Math.round((completedRuns / totalRuns) * 100)}%` : "—" },
          ].map(({ label, value }) => (
            <GlassCard key={label} className="p-4">
              <span className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] block">{label}</span>
              <p className="text-[24px] font-semibold text-[#F9FAFB] mt-1">{value}</p>
            </GlassCard>
          ))}
        </div>

        <GlassCard className="p-0">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(255,255,255,0.06)]">
            <h3 className="text-[14px] font-medium text-[#F9FAFB]">Workflow Traces</h3>
            <span className="text-[12px] text-[#4B5563]">All runs</span>
          </div>
          {loading ? (
            <div className="px-4 py-12 text-center text-[#9CA3AF]">Loading traces...</div>
          ) : workflows.length === 0 ? (
            <div className="px-4 py-12 text-center text-[#9CA3AF]">No workflow runs yet.</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)]">
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Run ID</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Agents</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Runtime</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Confidence</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Status</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Started</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Details</th>
                </tr>
              </thead>
              <tbody>
                {workflows.map((wf) => {
                  const wfTasks = tasks[wf.id] ?? []
                  return (
                    <tr
                      key={wf.id}
                      className="border-b border-[rgba(255,255,255,0.06)] last:border-b-0 hover:bg-[rgba(255,255,255,0.02)] transition-colors"
                    >
                      <td className="px-4 py-4">
                        <span className="text-[12px] font-mono text-[#8B5CF6]">{wf.id.slice(0, 8)}…</span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-1">
                          {wfTasks.length > 0 ? (
                            wfTasks.map(t => (
                              <span key={t.id} className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                                t.status === 'completed' ? 'bg-[rgba(16,185,129,0.1)] text-[#10B981]' :
                                t.status === 'failed' ? 'bg-[rgba(239,68,68,0.1)] text-[#EF4444]' :
                                'bg-[rgba(255,255,255,0.05)] text-[#9CA3AF]'
                              }`}>
                                {t.agent_name}
                              </span>
                            ))
                          ) : (
                            <span className="text-[12px] text-[#4B5563]">{wf.status === 'queued' ? 'Queued' : '—'}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4 text-[12px] font-mono text-[#9CA3AF]">
                        {wf.runtime_ms != null ? `${wf.runtime_ms}ms` : '—'}
                      </td>
                      <td className="px-4 py-4 text-[13px] text-[#F59E0B]">
                        {wf.confidence_score != null ? `${(wf.confidence_score * 100).toFixed(0)}%` : '—'}
                      </td>
                      <td className="px-4 py-4">
                        <Badge variant={getStatusBadge(wf.status) as any}>{wf.status}</Badge>
                      </td>
                      <td className="px-4 py-4 text-[12px] text-[#4B5563]">
                        {wf.started_at ? timeAgo(wf.started_at) : timeAgo(wf.created_at)}
                      </td>
                      <td className="px-4 py-4">
                        <a href={`/risk?run=${wf.id}`} className="text-[12px] text-[#8B5CF6] hover:text-[#A78BFA] flex items-center gap-1">
                          Findings <ExternalLink className="w-3 h-3" />
                        </a>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </GlassCard>
      </main>
    </div>
  )
}
