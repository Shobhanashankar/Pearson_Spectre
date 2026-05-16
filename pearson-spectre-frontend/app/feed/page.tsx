"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { GlassCard, Button } from "@/components/ui-components"
import { getRegulations, triggerRegulationPoll, Regulation } from "@/lib/api-client"

// Derive a short code from regulation name
function deriveCode(name: string): string {
  if (name.toUpperCase().includes("DPDP")) return "DPDP"
  if (name.toUpperCase().includes("GDPR")) return "GDPR"
  if (name.toUpperCase().includes("RBI")) return "RBI"
  if (name.toUpperCase().includes("SEBI")) return "SEBI"
  return name.slice(0, 6).toUpperCase()
}

const SOURCE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  DPDP: { bg: "rgba(20,184,166,0.1)", text: "#14B8A6", border: "rgba(20,184,166,0.25)" },
  GDPR: { bg: "rgba(59,130,246,0.1)", text: "#3B82F6", border: "rgba(59,130,246,0.25)" },
  RBI: { bg: "rgba(245,158,11,0.1)", text: "#F59E0B", border: "rgba(245,158,11,0.25)" },
  SEBI: { bg: "rgba(139,92,246,0.1)", text: "#8B5CF6", border: "rgba(139,92,246,0.25)" },
}

function getSourceStyle(code: string) {
  return SOURCE_COLORS[code] ?? { bg: "rgba(139,92,246,0.1)", text: "#8B5CF6", border: "rgba(139,92,246,0.25)" }
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
  } catch { return dateStr }
}

// Static fallback when DB has no regulations yet
const STATIC_REGULATIONS = [
  {
    id: "s1", name: "Digital Personal Data Protection Act 2023", code: "DPDP",
    version: "1.0", summary: "Enhanced breach notification requirements — 72h mandatory reporting for data fiduciaries. Significant penalties up to ₹250 crore for non-compliance.",
    fetched_at: new Date(Date.now() - 2 * 86400000).toISOString(), is_active: 1,
  },
  {
    id: "s2", name: "RBI Data Localisation Circular", code: "RBI",
    version: "2024.1", summary: "Payment data must reside on Indian servers; mirror copies abroad allowed after 24h local storage confirmed.",
    fetched_at: new Date(Date.now() - 3 * 86400000).toISOString(), is_active: 1,
  },
  {
    id: "s3", name: "General Data Protection Regulation", code: "GDPR",
    version: "2018 + EDPB AI Guidelines", summary: "Clarifies obligations for profiling and automated decisions affecting EU data subjects under Article 22.",
    fetched_at: new Date(Date.now() - 4 * 86400000).toISOString(), is_active: 1,
  },
]

export default function FeedPage() {
  const [regulations, setRegulations] = useState<(Regulation & { code?: string })[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)

  const loadRegulations = () => {
    return getRegulations().then(res => {
      if (res.data && res.data.length > 0) {
        const enriched = res.data.map(r => ({ ...r, code: deriveCode(r.name) }))
        setRegulations(enriched)
      } else {
        // Use static fallback
        setRegulations(STATIC_REGULATIONS as any)
      }
      if (res.error) setError(res.error)
      setLoading(false)
    })
  }

  useEffect(() => {
    loadRegulations()
  }, [])

  const handlePoll = async () => {
    setPolling(true)
    setError(null)
    const res = await triggerRegulationPoll()
    setError(res.error ?? res.data?.message ?? "Regulation feed poll triggered.")
    setTimeout(() => loadRegulations(), 800)
    setPolling(false)
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <TopBar
          title="Regulation Feed"
          subtitle="Live regulatory updates — any change here triggers autonomous re-analysis of your contracts"
          action={<Button onClick={handlePoll} disabled={polling}>{polling ? "Polling..." : "Trigger Poll"}</Button>}
        />

        {error && (
          <div className="mb-4 rounded-lg border border-[rgba(139,92,246,0.25)] bg-[rgba(139,92,246,0.08)] px-4 py-3 text-[12px] text-[#C4B5FD]">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-12 text-center text-[#9CA3AF]">Loading regulations...</div>
        ) : (
          <div className="space-y-4">
            {regulations.map((reg) => {
              const code = (reg as any).code ?? deriveCode(reg.name)
              const style = getSourceStyle(code)
              return (
                <GlassCard key={reg.id} className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span
                          className="text-[10px] font-semibold px-2 py-0.5 rounded border"
                          style={{ background: style.bg, color: style.text, borderColor: style.border }}
                        >
                          {code}
                        </span>
                        {reg.version && (
                          <span className="text-[11px] text-[#4B5563]">v{reg.version}</span>
                        )}
                        <span className="text-[12px] text-[#6B7280]">{formatDate(reg.fetched_at)}</span>
                        <span className="text-[11px] px-2 py-0.5 bg-[rgba(16,185,129,0.1)] text-[#10B981] border border-[rgba(16,185,129,0.25)] rounded">
                          Active
                        </span>
                      </div>
                      <h3 className="text-[14px] font-medium text-[#F9FAFB] mb-1">{reg.name}</h3>
                      {reg.summary && (
                        <p className="text-[13px] text-[#6B7280] leading-5">{reg.summary}</p>
                      )}
                      {reg.source_url && (
                        <a
                          href={reg.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] text-[#8B5CF6] hover:underline mt-1 block"
                        >
                          {reg.source_url}
                        </a>
                      )}
                    </div>
                    <div className="flex flex-col gap-2 shrink-0">
                      <Button variant="secondary" className="text-[11px] px-3 py-1 whitespace-nowrap">
                        View Details →
                      </Button>
                      <Button className="text-[11px] px-3 py-1 whitespace-nowrap">
                        Rescan Contracts
                      </Button>
                    </div>
                  </div>
                </GlassCard>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
