"use client"

import { useState, useCallback } from "react"
import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { GlassCard, Button, Badge } from "@/components/ui-components"
import { FileUp, FileText, X, Upload as UploadIcon, Zap, Play } from "lucide-react"
import { uploadContract, Contract, getContracts } from "@/lib/api-client"
import { useEffect } from "react"

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const [recentUploads, setRecentUploads] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)

  // Load recent contracts on component mount
  useEffect(() => {
    loadRecentContracts()
  }, [])

  const loadRecentContracts = async () => {
    try {
      const response = await getContracts()
      if (response.data) {
        setRecentUploads(response.data.slice(0, 5))
      }
    } catch (error) {
      console.error('Failed to load contracts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile?.type === "application/pdf") {
      setFile(droppedFile)
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile?.type === "application/pdf") {
      setFile(selectedFile)
    }
  }, [])

  const handleStartAnalysis = async () => {
    if (!file) return

    setIsUploading(true)
    setUploadStatus("Uploading contract...")

    try {
      const response = await uploadContract(file)
      if (response.status === 200 || response.status === 201 || response.data?.contract_id) {
        setUploadStatus("✓ Contract uploaded successfully! Analysis started.")
        setFile(null)
        setTimeout(() => {
          setUploadStatus(null)
          loadRecentContracts()
        }, 2000)
      } else {
        setUploadStatus(`✗ Upload failed: ${response.error || 'Unknown error'}`)
      }
    } catch (error) {
      setUploadStatus(`✗ Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsUploading(false)
    }
  }

  const buildDemoPdf = () => {
    const text = "Demo Vendor Agreement. The vendor may process personal data without consent and retain customer data forever. Payment data may be stored outside India by subprocessors at vendor discretion."
    const escaped = text.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)")
    const stream = `BT /F1 12 Tf 72 720 Td (${escaped}) Tj ET`
    const objects = [
      "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
      "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
      "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
      "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
      `5 0 obj << /Length ${stream.length} >> stream\n${stream}\nendstream endobj`,
    ]
    let pdf = "%PDF-1.4\n"
    const offsets = [0]
    objects.forEach((obj) => {
      offsets.push(pdf.length)
      pdf += `${obj}\n`
    })
    const xref = pdf.length
    pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
    offsets.slice(1).forEach((offset) => {
      pdf += `${String(offset).padStart(10, "0")} 00000 n \n`
    })
    pdf += `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
    return new File([pdf], "spectre-demo-contract.pdf", { type: "application/pdf" })
  }

  const handleLoadDemo = async () => {
    const demo = buildDemoPdf()
    setFile(demo)
    setIsUploading(true)
    setUploadStatus("Uploading demo contract...")
    const response = await uploadContract(demo)
    if (response.data?.contract_id) {
      setUploadStatus("✓ Demo contract uploaded. Analysis started.")
      setTimeout(() => {
        setUploadStatus(null)
        loadRecentContracts()
      }, 2000)
    } else {
      setUploadStatus(`✗ Demo upload failed: ${response.error || "Unknown error"}`)
    }
    setIsUploading(false)
  }

  const showConnectorNotice = (name: string) => {
    setUploadStatus(`${name} connector is not configured in this local build. Upload a PDF or load the demo contract.`)
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <div className="max-w-[680px] mx-auto">
          <TopBar
            title="Upload Contract"
            subtitle="Spectre will analyze your PDF against DPDP Act 2023, GDPR, and RBI data localisation guidelines."
          />

          {/* Upload Status Message */}
          {uploadStatus && (
            <div className={`p-3 rounded-lg mb-4 text-sm ${
              uploadStatus.includes('✓') 
                ? 'bg-green-900/30 text-green-200 border border-green-700' 
                : 'bg-red-900/30 text-red-200 border border-red-700'
            }`}>
              {uploadStatus}
            </div>
          )}

          {/* Upload Zone */}
          <GlassCard className="p-0 mb-4">
            <div
              className={`min-h-[220px] flex flex-col items-center justify-center p-8 border border-dashed rounded-xl m-1 transition-colors ${
                isDragOver
                  ? "border-[#8B5CF6] bg-[rgba(139,92,246,0.06)]"
                  : file
                  ? "border-[rgba(16,185,129,0.4)]"
                  : "border-[rgba(139,92,246,0.4)]"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {!file ? (
                <>
                  <FileUp className={`w-8 h-8 mb-3 ${isDragOver ? "text-[#A78BFA]" : "text-[#8B5CF6]"}`} />
                  <p className="text-[15px] text-[#F9FAFB] mb-1">Drop your contract PDF here</p>
                  <label className="text-[13px] text-[#4B5563] hover:underline cursor-pointer">
                    or click to browse files
                    <input
                      type="file"
                      accept=".pdf"
                      className="hidden"
                      onChange={handleFileSelect}
                    />
                  </label>
                  <p className="text-[11px] text-[#4B5563] mt-2">PDF only · max 10MB</p>
                </>
              ) : (
                <>
                  <FileText className="w-8 h-8 mb-3 text-[#10B981]" />
                  <p className="text-[14px] text-[#F9FAFB] truncate max-w-full">{file.name}</p>
                  <p className="text-[12px] text-[#4B5563] mb-4">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  <Button 
                    className="w-full max-w-[280px]"
                    onClick={handleStartAnalysis}
                    disabled={isUploading}
                  >
                    {isUploading ? "Uploading..." : "Start Analysis"}
                  </Button>
                  <button
                    onClick={() => setFile(null)}
                    disabled={isUploading}
                    className="text-[12px] text-[#EF4444] mt-3 hover:underline flex items-center gap-1 disabled:opacity-50"
                  >
                    <X className="w-3 h-3" /> Remove
                  </button>
                </>
              )}
            </div>
          </GlassCard>

          {/* Alternative Import Row */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <Button variant="secondary" className="flex items-center justify-center gap-2" onClick={() => showConnectorNotice("Google Drive")}>
              <UploadIcon className="w-4 h-4" /> Google Drive
            </Button>
            <Button variant="secondary" className="flex items-center justify-center gap-2" onClick={() => showConnectorNotice("DocuSign")}>
              <Zap className="w-4 h-4" /> DocuSign Webhook
            </Button>
            <Button variant="secondary" className="flex items-center justify-center gap-2" onClick={handleLoadDemo} disabled={isUploading}>
              <Play className="w-4 h-4" /> Load Demo Contract
            </Button>
          </div>

          {/* Regulations Card */}
          <GlassCard className="p-4 mb-4">
            <span className="text-[10px] uppercase tracking-[0.08em] text-[#6B7280] block mb-2">ANALYZED AGAINST</span>
            <div className="flex gap-2">
              <span className="text-[11px] px-2 py-1 bg-[rgba(20,184,166,0.1)] text-[#14B8A6] border border-[rgba(20,184,166,0.25)] rounded">
                DPDP Act 2023
              </span>
              <span className="text-[11px] px-2 py-1 bg-[rgba(59,130,246,0.1)] text-[#3B82F6] border border-[rgba(59,130,246,0.25)] rounded">
                GDPR
              </span>
              <span className="text-[11px] px-2 py-1 bg-[rgba(245,158,11,0.1)] text-[#F59E0B] border border-[rgba(245,158,11,0.25)] rounded">
                RBI Guidelines
              </span>
            </div>
          </GlassCard>

          {/* Recent Uploads */}
          <GlassCard className="p-0">
            <div className="px-4 py-3 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-[14px] font-medium text-[#F9FAFB]">Recent Uploads</h3>
            </div>
            {loading ? (
              <div className="px-4 py-8 text-center text-[#9CA3AF]">Loading contracts...</div>
            ) : recentUploads.length === 0 ? (
              <div className="px-4 py-8 text-center text-[#9CA3AF]">No contracts uploaded yet</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[rgba(255,255,255,0.06)]">
                    <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-2">Filename</th>
                    <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-2">Uploaded</th>
                    <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-2">Status</th>
                    <th className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] font-medium text-left px-4 py-2">Size</th>
                  </tr>
                </thead>
                <tbody>
                  {recentUploads.map((upload) => (
                    <tr key={upload.id} className="border-b border-[rgba(255,255,255,0.06)] last:border-b-0 hover:bg-[rgba(255,255,255,0.02)] cursor-pointer">
                      <td className="px-4 py-3 text-[13px] text-[#F9FAFB] truncate max-w-[200px]">{upload.original_name}</td>
                      <td className="px-4 py-3 text-[12px] text-[#4B5563]">{new Date(upload.uploaded_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3">
                        <Badge variant={upload.status as any}>{upload.status}</Badge>
                      </td>
                      <td className="px-4 py-3 text-[13px] text-[#F59E0B]">{(upload.file_size / 1024 / 1024).toFixed(1)} MB</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </GlassCard>
        </div>
      </main>
    </div>
  )
}
