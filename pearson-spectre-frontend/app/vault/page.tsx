"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { GlassCard, Badge, Button } from "@/components/ui-components"
import { getContracts, getContractFindings, deleteContract, Contract, Finding, getStoredUser } from "@/lib/api-client"
import { Trash2, ExternalLink } from "lucide-react"

function timeAgo(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function VaultPage() {
  const router = useRouter()
  const [contracts, setContracts] = useState<Contract[]>([])
  const [findingsCounts, setFindingsCounts] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const user = getStoredUser()

  const load = async () => {
    const res = await getContracts()
    if (res.data) {
      setContracts(res.data)
      // Load finding counts for each contract
      res.data.forEach(async (c) => {
        if (c.status === 'analysed') {
          const fRes = await getContractFindings(c.id)
          if (fRes.data) {
            setFindingsCounts(prev => ({ ...prev, [c.id]: fRes.data!.length }))
          }
        }
      })
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return
    const res = await deleteContract(id)
    if (res.status === 200) load()
    else alert(res.error || 'Delete failed')
  }

  const getStatusBadge = (status: string) => {
    if (status === 'analysed') return 'complete'
    if (status === 'processing') return 'running'
    if (status === 'error') return 'violation'
    return 'running'
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <TopBar
          title="Contract Vault"
          subtitle="All uploaded contracts and their compliance status"
          action={
            <Link href="/upload"><Button>Upload Contract</Button></Link>
          }
        />

        <GlassCard className="p-0">
          {loading ? (
            <div className="px-4 py-12 text-center text-[#9CA3AF]">Loading contracts...</div>
          ) : contracts.length === 0 ? (
            <div className="px-4 py-12 text-center text-[#9CA3AF]">
              No contracts yet.{" "}
              <Link href="/upload" className="text-[#8B5CF6] hover:underline">Upload one</Link> to get started.
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)]">
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Contract Name</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Uploaded</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Status</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Size</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Findings</th>
                  <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {contracts.map((contract) => (
                  <tr
                    key={contract.id}
                    className="border-b border-[rgba(255,255,255,0.06)] last:border-b-0 hover:bg-[rgba(255,255,255,0.02)] cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-4">
                      <span className="text-[13px] text-[#F9FAFB]">{contract.original_name}</span>
                    </td>
                    <td className="px-4 py-4 text-[12px] text-[#4B5563]">{timeAgo(contract.uploaded_at)}</td>
                    <td className="px-4 py-4">
                      <Badge variant={getStatusBadge(contract.status) as any}>{contract.status}</Badge>
                    </td>
                    <td className="px-4 py-4 text-[13px] text-[#F59E0B]">
                      {(contract.file_size / 1024 / 1024).toFixed(1)} MB
                    </td>
                    <td className="px-4 py-4">
                      <span className={`text-[13px] ${(findingsCounts[contract.id] ?? 0) > 0 ? 'text-[#EF4444]' : 'text-[#10B981]'}`}>
                        {contract.status === 'analysed' ? (findingsCounts[contract.id] ?? '…') : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-3">
                        <Link
                          href={`/risk?contract=${contract.id}`}
                          className="text-[12px] text-[#8B5CF6] hover:text-[#A78BFA]"
                        >
                          View Analysis →
                        </Link>
                        {user?.role === 'admin' && (
                          <button
                            onClick={() => handleDelete(contract.id, contract.original_name)}
                            className="text-[#6B7280] hover:text-[#EF4444] transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </GlassCard>
      </main>
    </div>
  )
}
