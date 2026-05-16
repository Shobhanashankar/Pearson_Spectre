"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { login, setToken, setStoredUser, isAuthenticated } from "@/lib/api-client"
import { Shield } from "lucide-react"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("admin@spectre.ai")
  const [password, setPassword] = useState("admin123")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) router.replace("/")
  }, [router])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const res = await login(email, password)
    if (res.data?.access_token) {
      setToken(res.data.access_token)
      setStoredUser({
        name: res.data.name,
        role: res.data.role,
        email,
        user_id: res.data.user_id,
      })
      router.replace("/")
    } else {
      setError(res.error || "Login failed. Check credentials.")
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#070912]">
      <div className="w-full max-w-[400px] p-8">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-10 justify-center">
          <div className="w-9 h-9 bg-[rgba(139,92,246,0.15)] border border-[rgba(139,92,246,0.3)] rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-[#8B5CF6]" />
          </div>
          <div>
            <span className="text-[15px] font-semibold text-[#F9FAFB]">Pearson Spectre</span>
            <span className="text-[10px] text-[#4B5563] block">AI Contract Compliance</span>
          </div>
        </div>

        <div className="bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] rounded-xl p-6">
          <h1 className="text-[18px] font-semibold text-[#F9FAFB] mb-1">Sign in</h1>
          <p className="text-[13px] text-[#6B7280] mb-6">Enter your credentials to access the platform</p>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] block mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2.5 text-[13px] text-[#F9FAFB] outline-none focus:border-[rgba(139,92,246,0.5)] transition-colors"
                placeholder="admin@spectre.ai"
                required
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-[0.08em] text-[#6B7280] block mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)] rounded-lg px-3 py-2.5 text-[13px] text-[#F9FAFB] outline-none focus:border-[rgba(139,92,246,0.5)] transition-colors"
                placeholder="••••••••"
                required
              />
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-900/20 border border-red-700/30 text-[12px] text-red-300">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#8B5CF6] hover:bg-[#7C3AED] text-white text-[13px] font-medium py-2.5 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div className="mt-5 pt-4 border-t border-[rgba(255,255,255,0.06)]">
            <p className="text-[11px] text-[#4B5563] text-center mb-2">Demo accounts</p>
            <div className="grid grid-cols-3 gap-2">
              {[
                { email: "admin@spectre.ai", pw: "admin123", label: "Admin" },
                { email: "legal@spectre.ai", pw: "legal123", label: "Legal" },
                { email: "security@spectre.ai", pw: "security123", label: "Security" },
              ].map((acc) => (
                <button
                  key={acc.label}
                  type="button"
                  onClick={() => { setEmail(acc.email); setPassword(acc.pw) }}
                  className="text-[10px] py-1.5 px-2 rounded border border-[rgba(255,255,255,0.06)] text-[#6B7280] hover:text-[#9CA3AF] hover:border-[rgba(255,255,255,0.12)] transition-colors"
                >
                  {acc.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
