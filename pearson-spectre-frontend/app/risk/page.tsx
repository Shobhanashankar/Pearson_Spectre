"use client"

import { Suspense, useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { GlassCard, Badge, Button } from "@/components/ui-components"
import {
  getContracts, getContractFindings, getWorkflowFindings,
  Contract, Finding
} from "@/lib/api-client"
import Link from "next/link"

function RiskContent() {
  const searchParams = useSearchParams()
  const contractParam = searchParams.get('contract')
  const runParam = searchParams.get('run')

  const [contracts, setContracts] = useState<Contract[]>([])
  const [selectedContract, setSelectedContract] = useState<string | null>(contractParam)
  const [findings, setFindings] = useState<Finding[]>([])
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
  const [loading, setLoading] = useState(true)
  const [findingsLoading, setFindingsLoading] = useState(false)
  const [actionStatus, setActionStatus] = useState<string | null>(null)

  // Load contracts for selector
  useEffect(() => {
    getContracts().then(res => {
      if (res.data) {
        setContracts(res.data.filter(c => c.status === 'analysed'))
        if (!selectedContract && res.data.length > 0) {
          const analysed = res.data.find(c => c.status === 'analysed')
          if (analysed) setSelectedContract(analysed.id)
        }
      }
      setLoading(false)
    })
  }, [])

  // Load findings when contract changes
  useEffect(() => {
    if (!selectedContract && !runParam) return
    setFindingsLoading(true)
    setSelectedFinding(null)

    const loadFindings = async () => {
      let res
      if (runParam) {
        res = await getWorkflowFindings(runParam)
      } else if (selectedContract) {
        res = await getContractFindings(selectedContract)
      }
      if (res?.data) {
        setFindings(res.data)
        if (res.data.length > 0) setSelectedFinding(res.data[0])
      } else {
        setFindings([])
      }
      setFindingsLoading(false)
    }

    loadFindings()
  }, [selectedContract, runParam])

  const getContractName = (id: string) => {
    return contracts.find(c => c.id === id)?.original_name ?? id
  }

  const exportFinding = () => {
    if (!selectedFinding) return
    const blob = new Blob([JSON.stringify(selectedFinding, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `spectre-finding-${selectedFinding.id}.json`
    a.click()
    URL.revokeObjectURL(url)
    setActionStatus("Finding exported.")
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <TopBar
          title="Risk Analysis"
          subtitle="Compliance findings and clause redlines"
        />

        {actionStatus && (
          <div className="mb-4 p-3 rounded-lg text-sm bg-[rgba(16,185,129,0.12)] text-[#A7F3D0] border border-[rgba(16,185,129,0.25)]">
            {actionStatus}
          </div>
        )}

        {/* Contract Selector */}
        {!runParam && (
          <div className="mb-6 flex items-center gap-3">
            <label className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280]">Contract:</label>
            {loading ? (
              <span className="text-[13px] text-[#4B5563]">Loading...</span>
            ) : contracts.length === 0 ? (
              <span className="text-[13px] text-[#4B5563]">
                No analysed contracts yet.{" "}
                <Link href="/upload" className="text-[#8B5CF6] hover:underline">Upload one</Link>
              </span>
            ) : (
              <select
                value={selectedContract ?? ''}
                onChange={(e) => setSelectedContract(e.target.value)}
                className="bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-1.5 text-[13px] text-[#F9FAFB] outline-none focus:border-[rgba(139,92,246,0.5)]"
              >
                {contracts.map(c => (
                  <option key={c.id} value={c.id}>{c.original_name}</option>
                ))}
              </select>
            )}
            {findings.length > 0 && (
              <span className="text-[12px] text-[#6B7280]">{findings.length} findings</span>
            )}
          </div>
        )}

        {runParam && (
          <div className="mb-6">
            <p className="text-[12px] text-[#6B7280]">
              Showing findings for run: <span className="font-mono text-[#8B5CF6]">{runParam.slice(0, 16)}…</span>
            </p>
          </div>
        )}

        {findingsLoading ? (
          <div className="flex items-center justify-center py-20 text-[#9CA3AF]">Analyzing...</div>
        ) : findings.length === 0 && (selectedContract || runParam) ? (
          <GlassCard className="p-8 text-center text-[#9CA3AF]">
            No findings for this contract yet. Analysis may still be running.
          </GlassCard>
        ) : findings.length > 0 ? (
          <div className="grid grid-cols-[55fr_45fr] gap-6">
            {/* Findings Table */}
            <GlassCard className="p-0">
              <div className="px-4 py-3 border-b border-[rgba(255,255,255,0.06)]">
                <h3 className="text-[14px] font-medium text-[#F9FAFB]">Findings</h3>
              </div>
              <div className="overflow-y-auto max-h-[600px]">
                <table className="w-full">
                  <thead className="sticky top-0 bg-[#0D1117]">
                    <tr className="border-b border-[rgba(255,255,255,0.06)]">
                      <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-2">Clause</th>
                      <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-2">Severity</th>
                      <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-2">Confidence</th>
                      <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-2">Regulation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {findings.map((finding) => (
                      <tr
                        key={finding.id}
                        onClick={() => setSelectedFinding(finding)}
                        className={`border-b border-[rgba(255,255,255,0.06)] last:border-b-0 cursor-pointer transition-colors ${
                          selectedFinding?.id === finding.id
                            ? "bg-[rgba(139,92,246,0.06)] border-l-2 border-l-[#8B5CF6]"
                            : "hover:bg-[rgba(255,255,255,0.02)]"
                        }`}
                      >
                        <td className="px-4 py-3">
                          <p className="text-[13px] text-[#F9FAFB] truncate max-w-[180px]">
                            {finding.clause_text?.slice(0, 40) || `Clause #${finding.clause_index}`}
                          </p>
                          <p className="text-[11px] text-[#4B5563]">Index {finding.clause_index}</p>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={finding.severity as any}>{finding.severity}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-[50px] h-1 rounded-full bg-[rgba(255,255,255,0.06)] overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  finding.confidence > 0.8 ? "bg-[#10B981]" :
                                  finding.confidence > 0.6 ? "bg-[#F59E0B]" : "bg-[#EF4444]"
                                }`}
                                style={{ width: `${finding.confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-[11px] text-[#9CA3AF]">{(finding.confidence * 100).toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-[11px] text-[#9CA3AF] max-w-[100px] truncate">
                          {finding.regulation_ref ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>

            {/* Detail / Redline Panel */}
            {selectedFinding && (
              <GlassCard className="p-0">
                <div className="flex items-center justify-between px-4 py-3 border-b border-[rgba(255,255,255,0.06)]">
                  <div>
                    <h3 className="text-[14px] font-medium text-[#F9FAFB]">Clause Redline</h3>
                    <p className="text-[11px] text-[#4B5563]">Clause #{selectedFinding.clause_index}</p>
                  </div>
                  {selectedFinding.regulation_ref && (
                    <span className="text-[11px] px-2 py-1 bg-[rgba(20,184,166,0.1)] text-[#14B8A6] border border-[rgba(20,184,166,0.25)] rounded">
                      {selectedFinding.regulation_ref}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 divide-y divide-[rgba(255,255,255,0.06)]">
                  {selectedFinding.original_text && (
                    <div className="p-4">
                      <span className="text-[11px] uppercase text-[#EF4444] font-medium block mb-2">ORIGINAL</span>
                      <p className="text-[13px] leading-6 text-[#D1D5DB]">
                        <span className="bg-[rgba(239,68,68,0.1)] text-[#FCA5A5] px-0.5 rounded">
                          {selectedFinding.original_text}
                        </span>
                      </p>
                    </div>
                  )}
                  {selectedFinding.rewrite_suggestion && (
                    <div className="p-4">
                      <span className="text-[11px] uppercase text-[#10B981] font-medium block mb-2">PROPOSED REWRITE</span>
                      <p className="text-[13px] leading-6 text-[#D1D5DB]">
                        <span className="bg-[rgba(16,185,129,0.1)] text-[#6EE7B7] px-0.5 rounded">
                          {selectedFinding.rewrite_suggestion}
                        </span>
                      </p>
                    </div>
                  )}
                  {selectedFinding.clause_text && (
                    <div className="p-4">
                      <span className="text-[11px] uppercase text-[#6B7280] font-medium block mb-2">CLAUSE TEXT</span>
                      <p className="text-[12px] leading-6 text-[#9CA3AF]">{selectedFinding.clause_text}</p>
                    </div>
                  )}
                  {selectedFinding.regulation_cite && (
                    <div className="p-4">
                      <span className="text-[11px] uppercase text-[#6B7280] font-medium block mb-2">REGULATION REFERENCE</span>
                      <p className="text-[12px] text-[#9CA3AF]">{selectedFinding.regulation_cite}</p>
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 px-4 py-3 border-t border-[rgba(255,255,255,0.06)]">
                  <Button onClick={() => setActionStatus("GitHub PR creation runs automatically after analysis when GITHUB_TOKEN and GITHUB_REPO are configured.")}>Generate PR</Button>
                  <Button variant="secondary" onClick={exportFinding}>Export JSON</Button>
                  <Button variant="secondary" onClick={() => setActionStatus("Legal notification runs automatically after analysis when SLACK_WEBHOOK_URL is configured.")}>Notify Legal</Button>
                </div>
              </GlassCard>
            )}
          </div>
        ) : null}
      </main>
    </div>
  )
}

export default function RiskPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#070912]" />}>
      <RiskContent />
    </Suspense>
  )
}
