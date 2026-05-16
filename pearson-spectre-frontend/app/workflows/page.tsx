"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { GlassCard, Badge, Button } from "@/components/ui-components"
import { getWorkflows, getContracts, getWorkflowFindings, WorkflowRun, Contract } from "@/lib/api-client"

function timeAgo(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<WorkflowRun[]>([])
  const [contracts, setContracts] = useState<Record<string, Contract>>({})
  const [severities, setSeverities] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      const [wfRes, cRes] = await Promise.all([getWorkflows(), getContracts()])
      if (wfRes.data) {
        setWorkflows(wfRes.data)
        // Load top severity for completed runs
        wfRes.data.forEach(async (wf) => {
          if (wf.status === 'completed') {
            const fRes = await getWorkflowFindings(wf.id)
            if (fRes.data && fRes.data.length > 0) {
              const sev = fRes.data[0].severity
              setSeverities(prev => ({ ...prev, [wf.id]: sev }))
            }
          }
        })
      }
      if (cRes.data) {
        const map: Record<string, Contract> = {}
        cRes.data.forEach(c => { map[c.id] = c })
        setContracts(map)
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

  const getSeverityBadge = (runId: string, status: string) => {
    if (status !== 'completed') return null
    const sev = severities[runId]
    if (!sev) return null
    return <Badge variant={sev as any}>{sev}</Badge>
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <TopBar
          title="Workflows"
          subtitle="All contract analysis workflows"
          action={
            <Link href="/upload"><Button>New Analysis</Button></Link>
          }
        />

        <GlassCard className="p-0">
          {loading ? (
            <div className="px-4 py-12 text-center text-[#9CA3AF]">Loading workflows...</div>
          ) : workflows.length === 0 ? (
            <div className="px-4 py-12 text-center text-[#9CA3AF]">
              No workflows yet.{" "}
              <Link href="/upload" className="text-[#8B5CF6] hover:underline">Upload a contract</Link> to start.
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)]">
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Run ID</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Contract</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Top Severity</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Status</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Confidence</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Runtime</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Started</th>
                </tr>
              </thead>
              <tbody>
                {workflows.map((wf) => {
                  const contract = contracts[wf.contract_id]
                  return (
                    <tr
                      key={wf.id}
                      className="border-b border-[rgba(255,255,255,0.06)] last:border-b-0 hover:bg-[rgba(255,255,255,0.02)] cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-4">
                        <Link href={`/workflows/${wf.id}`} className="text-[11px] font-mono text-[#8B5CF6] hover:text-[#A78BFA]">
                          {wf.id.slice(0, 8)}…
                        </Link>
                      </td>
                      <td className="px-4 py-4">
                        <p className="text-[13px] text-[#F9FAFB] truncate max-w-[200px]">
                          {contract?.original_name ?? wf.contract_id.slice(0, 12) + '...'}
                        </p>
                        <p className="text-[11px] text-[#4B5563] capitalize">{wf.trigger_source}</p>
                      </td>
                      <td className="px-4 py-4">
                        {getSeverityBadge(wf.id, wf.status) ?? <span className="text-[12px] text-[#4B5563]">—</span>}
                      </td>
                      <td className="px-4 py-4">
                        <Badge variant={getStatusBadge(wf.status) as any}>{wf.status}</Badge>
                      </td>
                      <td className="px-4 py-4">
                        <span className="text-[13px] text-[#F59E0B]">
                          {wf.confidence_score != null ? `${(wf.confidence_score * 100).toFixed(0)}%` : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-[12px] text-[#4B5563]">
                        {wf.runtime_ms != null ? `${wf.runtime_ms}ms` : '—'}
                      </td>
                      <td className="px-4 py-4 text-[12px] text-[#4B5563]">
                        {timeAgo(wf.created_at)}
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
