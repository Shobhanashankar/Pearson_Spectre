"use client"

import { Sidebar } from "@/components/sidebar"
import { TopBar } from "@/components/top-bar"
import { GlassCard, Button } from "@/components/ui-components"

export default function SettingsPage() {
  const showConfigured = () => {
    window.alert("Configuration is read from anvil-backend/.env and pearson-spectre-frontend/.env.local.")
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="ml-[248px] p-8">
        <TopBar
          title="Settings"
          subtitle="Configure Spectre integrations and preferences"
        />

        <div className="max-w-[800px] space-y-6">
          {/* Integrations */}
          <GlassCard className="p-0">
            <div className="px-4 py-3 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-[14px] font-medium text-[#F9FAFB]">Integrations</h3>
            </div>
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-[rgba(255,255,255,0.06)]">
                <div>
                  <p className="text-[13px] text-[#F9FAFB]">Google Drive</p>
                  <p className="text-[11px] text-[#4B5563]">Auto-import contracts from shared folders</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-2 py-0.5 bg-[rgba(16,185,129,0.12)] text-[#10B981] rounded">Connected</span>
                  <Button variant="secondary" className="text-[11px] px-3 py-1" onClick={showConfigured}>Configure</Button>
                </div>
              </div>
              <div className="flex items-center justify-between py-3 border-b border-[rgba(255,255,255,0.06)]">
                <div>
                  <p className="text-[13px] text-[#F9FAFB]">DocuSign</p>
                  <p className="text-[11px] text-[#4B5563]">Webhook integration for signed contracts</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-2 py-0.5 bg-[rgba(16,185,129,0.12)] text-[#10B981] rounded">Connected</span>
                  <Button variant="secondary" className="text-[11px] px-3 py-1" onClick={showConfigured}>Configure</Button>
                </div>
              </div>
              <div className="flex items-center justify-between py-3 border-b border-[rgba(255,255,255,0.06)]">
                <div>
                  <p className="text-[13px] text-[#F9FAFB]">Slack</p>
                  <p className="text-[11px] text-[#4B5563]">Send alerts to #legal-alerts channel</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-2 py-0.5 bg-[rgba(16,185,129,0.12)] text-[#10B981] rounded">Connected</span>
                  <Button variant="secondary" className="text-[11px] px-3 py-1" onClick={showConfigured}>Configure</Button>
                </div>
              </div>
              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-[13px] text-[#F9FAFB]">GitHub</p>
                  <p className="text-[11px] text-[#4B5563]">Create PRs for contract redlines</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-2 py-0.5 bg-[rgba(16,185,129,0.12)] text-[#10B981] rounded">Connected</span>
                  <Button variant="secondary" className="text-[11px] px-3 py-1" onClick={showConfigured}>Configure</Button>
                </div>
              </div>
            </div>
          </GlassCard>

          {/* Omium Settings */}
          <GlassCard className="p-0">
            <div className="px-4 py-3 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-[14px] font-medium text-[#F9FAFB]">Omium Configuration</h3>
            </div>
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-[rgba(255,255,255,0.06)]">
                <div>
                  <p className="text-[13px] text-[#F9FAFB]">API Endpoint</p>
                  <p className="text-[11px] font-mono text-[#4B5563]">https://omium.spectre.ai/v1</p>
                </div>
                <Button variant="secondary" className="text-[11px] px-3 py-1" onClick={showConfigured}>Edit</Button>
              </div>
              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="text-[13px] text-[#F9FAFB]">Trace Retention</p>
                  <p className="text-[11px] text-[#4B5563]">30 days</p>
                </div>
                <Button variant="secondary" className="text-[11px] px-3 py-1" onClick={showConfigured}>Edit</Button>
              </div>
            </div>
          </GlassCard>

          {/* Regulation Sources */}
          <GlassCard className="p-0">
            <div className="px-4 py-3 border-b border-[rgba(255,255,255,0.06)]">
              <h3 className="text-[14px] font-medium text-[#F9FAFB]">Regulation Sources</h3>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <input type="checkbox" id="dpdp" defaultChecked className="w-4 h-4 rounded bg-transparent border-[rgba(255,255,255,0.2)]" />
                <label htmlFor="dpdp" className="text-[13px] text-[#F9FAFB]">DPDP Act 2023</label>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="gdpr" defaultChecked className="w-4 h-4 rounded bg-transparent border-[rgba(255,255,255,0.2)]" />
                <label htmlFor="gdpr" className="text-[13px] text-[#F9FAFB]">GDPR</label>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="rbi" defaultChecked className="w-4 h-4 rounded bg-transparent border-[rgba(255,255,255,0.2)]" />
                <label htmlFor="rbi" className="text-[13px] text-[#F9FAFB]">RBI Data Localisation Guidelines</label>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="sebi" className="w-4 h-4 rounded bg-transparent border-[rgba(255,255,255,0.2)]" />
                <label htmlFor="sebi" className="text-[13px] text-[#F9FAFB]">SEBI Cybersecurity Framework</label>
              </div>
            </div>
          </GlassCard>

          <div className="flex justify-end">
            <Button onClick={() => window.alert("Settings saved for this session. Persistent integration values live in the .env files.")}>Save Changes</Button>
          </div>
        </div>
      </main>
    </div>
  )
}
