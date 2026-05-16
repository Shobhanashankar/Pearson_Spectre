"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { Sidebar } from "@/components/sidebar"
import { GlassCard, Badge, Button } from "@/components/ui-components"
import { Check, X, ChevronDown, ChevronUp, ExternalLink, Loader2 } from "lucide-react"
import Link from "next/link"
import {
  getWorkflow, getWorkflowTasks, getWorkflowFindings, getContract,
  WorkflowRun, AgentTask, Finding, Contract
} from "@/lib/api-client"

function fmt(ms?: number) {
  if (!ms) return "—"
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function timeStr(s?: string) {
  if (!s) return "—"
  return new Date(s).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
}

const AGENT_ORDER = ["ingest", "extraction", "research", "classifier", "redline", "reporter"]

export default function WorkflowDetailPage() {
  const params = useParams()
  const runId = params.id as string

  const [workflow, setWorkflow] = useState<WorkflowRun | null>(null)
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [contract, setContract] = useState<Contract | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedLogs, setExpandedLogs] = useState<string[]>([])

  const load = async () => {
    if (!runId) return
    const [wfRes, tasksRes, findingsRes] = await Promise.all([
      getWorkflow(runId),
      getWorkflowTasks(runId),
      getWorkflowFindings(runId),
    ])
    if (wfRes.data) {
      setWorkflow(wfRes.data)
      const cRes = await getContract(wfRes.data.contract_id)
      if (cRes.data) setContract(cRes.data)
    }
    if (tasksRes.data) setTasks(tasksRes.data)
    if (findingsRes.data) setFindings(findingsRes.data)
    setLoading(false)
  }

  useEffect(() => {
    load()
    // Poll every 5s if still running
    const interval = setInterval(() => {
      if (workflow?.status === "running" || workflow?.status === "queued") load()
    }, 5000)
    return () => clearInterval(interval)
  }, [runId, workflow?.status])

  const toggleLogs = (id: string) => {
    setExpandedLogs(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id])
  }

  const getTaskIcon = (status: string) => {
    if (status === "completed") return (
      <div className="w-6 h-6 rounded-full bg-[#10B981] flex items-center justify-center shrink-0">
        <Check className="w-3 h-3 text-white" />
      </div>
    )
    if (status === "running") return (
      <div className="w-6 h-6 rounded-full border-2 border-[#8B5CF6] flex items-center justify-center shrink-0 animate-spin">
        <Loader2 className="w-3 h-3 text-[#8B5CF6]" />
      </div>
    )
    if (status === "failed") return (
      <div className="w-6 h-6 rounded-full bg-[#EF4444] flex items-center justify-center shrink-0">
        <X className="w-3 h-3 text-white" />
      </div>
    )
    return <div className="w-6 h-6 rounded-full border border-[rgba(255,255,255,0.15)] shrink-0" />
  }

  // Build full timeline: combine known agents with actual tasks
  const allAgents = AGENT_ORDER.map(agentName => {
    const task = tasks.find(t => t.agent_name === agentName)
    return {
      id: agentName,
      name: agentName.charAt(0).toUpperCase() + agentName.slice(1) + " Agent",
      status: task?.status ?? (workflow?.status === "completed" ? "completed" : "pending"),
      runtime_ms: task?.runtime_ms,
      error_msg: task?.error_msg,
      started_at: task?.started_at,
      completed_at: task?.completed_at,
    }
  })

  const highSeverity = findings.filter(f => f.severity === "high" || f.severity === "violation").length

  if (loading) return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#8B5CF6] border-t-transparent rounded-full animate-spin" />
      </main>
    </div>
  )

  if (!workflow) return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <p className="text-[#EF4444]">Workflow not found.</p>
        <Link href="/workflows" className="text-[#8B5CF6] text-[13px] mt-2 block">← Back to Workflows</Link>
      </main>
    </div>
  )

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-[16px] font-mono text-[#F9FAFB]">{runId.slice(0, 16)}…</h1>
              <p className="text-[13px] text-[#4B5563] mt-0.5">
                <Link href="/workflows" className="hover:text-[#8B5CF6]">Workflows</Link>
                {" → "}{contract?.original_name ?? workflow.contract_id.slice(0, 12) + "…"}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={workflow.status}>{workflow.status}</Badge>
              {workflow.runtime_ms && (
                <span className="text-[13px] font-mono text-[#9CA3AF]">{fmt(workflow.runtime_ms)}</span>
              )}
            </div>
          </div>
          <div className="h-px bg-[rgba(255,255,255,0.06)] mt-4" />
        </div>

        {/* 3-Column Layout */}
        <div className="grid grid-cols-[220px_1fr_280px] gap-6">
          {/* Left — Metadata */}
          <div className="space-y-4">
            <GlassCard className="p-4">
              <span className="text-[10px] uppercase tracking-[0.08em] text-[#6B7280] block mb-3">WORKFLOW</span>
              <div className="space-y-2.5">
                {[
                  ["Contract", contract?.original_name ?? "—"],
                  ["Trigger", workflow.trigger_source],
                  ["Started", timeStr(workflow.started_at ?? workflow.created_at)],
                  ["Runtime", fmt(workflow.runtime_ms)],
                  ["Confidence", workflow.confidence_score ? `${(workflow.confidence_score * 100).toFixed(0)}%` : "—"],
                  ["High Severity", highSeverity > 0 ? `${highSeverity} found` : "None"],
                ].map(([label, val]) => (
                  <div key={label} className="flex justify-between text-[12px]">
                    <span className="text-[#6B7280]">{label}</span>
                    <span className={`text-[#F9FAFB] truncate ml-2 max-w-[110px] ${label === "High Severity" && highSeverity > 0 ? "text-[#EF4444]" : ""}`}>{val}</span>
                  </div>
                ))}
              </div>

              <div className="h-px bg-[rgba(255,255,255,0.06)] my-4" />

              <span className="text-[10px] uppercase tracking-[0.08em] text-[#6B7280] block mb-3">AGENTS</span>
              <div className="space-y-1.5">
                {allAgents.map(agent => (
                  <div key={agent.id} className="flex justify-between items-center text-[12px] font-mono py-1 px-2 bg-[rgba(255,255,255,0.02)] rounded">
                    <span className="text-[#9CA3AF] capitalize">{agent.id}</span>
                    <Badge variant={agent.status} className="text-[8px]">{agent.status}</Badge>
                  </div>
                ))}
              </div>

              <div className="h-px bg-[rgba(255,255,255,0.06)] my-4" />

              <Link href={`/risk?run=${runId}`}>
                <Button variant="secondary" className="w-full flex items-center justify-center gap-2">
                  View Findings <ExternalLink className="w-3 h-3" />
                </Button>
              </Link>
            </GlassCard>
          </div>

          {/* Center — Timeline */}
          <GlassCard className="p-4">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="text-[14px] font-medium text-[#F9FAFB]">Execution Timeline</h3>
              <Badge variant={workflow.status}>{workflow.status}</Badge>
            </div>

            <div className="relative">
              <div className="absolute left-3 top-3 bottom-3 w-px bg-[rgba(255,255,255,0.1)]" />
              <div className="space-y-0">
                {allAgents.map(step => (
                  <div key={step.id} className="relative flex gap-4 py-3">
                    <div className="relative z-10">{getTaskIcon(step.status)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-[13px] font-medium text-[#F9FAFB]">{step.name}</span>
                        {step.runtime_ms && (
                          <span className="text-[11px] font-mono text-[#4B5563]">{fmt(step.runtime_ms)}</span>
                        )}
                      </div>
                      {step.started_at && (
                        <p className="text-[11px] text-[#4B5563] mt-0.5">
                          Started {timeStr(step.started_at)}
                        </p>
                      )}
                      {step.error_msg && (
                        <p className="text-[11px] text-[#EF4444] mt-1">{step.error_msg}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </GlassCard>

          {/* Right — Findings summary */}
          <GlassCard className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[14px] font-medium text-[#F9FAFB]">Findings</h3>
              <span className="text-[11px] font-mono text-[#4B5563]">{findings.length} total</span>
            </div>

            {findings.length === 0 ? (
              <p className="text-[13px] text-[#4B5563]">
                {workflow.status === "completed" ? "No findings." : "Pending analysis…"}
              </p>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {findings.slice(0, 10).map(f => (
                  <div key={f.id} className="p-2 rounded bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.06)]">
                    <div className="flex items-center justify-between mb-1">
                      <Badge variant={f.severity}>{f.severity}</Badge>
                      <span className="text-[10px] font-mono text-[#4B5563]">{(f.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p className="text-[11px] text-[#9CA3AF] line-clamp-2">{f.clause_text?.slice(0, 80)}…</p>
                    {f.regulation_ref && (
                      <p className="text-[10px] text-[#14B8A6] mt-1">{f.regulation_ref}</p>
                    )}
                  </div>
                ))}
                {findings.length > 10 && (
                  <p className="text-[11px] text-[#4B5563] text-center">+{findings.length - 10} more</p>
                )}
              </div>
            )}

            <div className="h-px bg-[rgba(255,255,255,0.06)] my-4" />

            <div className="grid grid-cols-2 gap-3 text-[12px]">
              {[
                ["Total", findings.length],
                ["High/Violation", findings.filter(f => ["high", "violation"].includes(f.severity)).length],
                ["Medium", findings.filter(f => f.severity === "medium").length],
                ["Low", findings.filter(f => f.severity === "low").length],
              ].map(([label, val]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[#6B7280]">{label}</span>
                  <span className="text-[#F9FAFB]">{val}</span>
                </div>
              ))}
            </div>

            <Link href={`/risk?run=${runId}`}>
              <Button variant="secondary" className="w-full mt-4 flex items-center justify-center gap-2">
                Full Analysis <ExternalLink className="w-3 h-3" />
              </Button>
            </Link>
          </GlassCard>
        </div>
      </main>
    </div>
  )
}
