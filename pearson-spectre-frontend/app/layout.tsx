import type { Metadata } from 'next'
import { Analytics } from '@vercel/analytics/next'
import { AuthGuard } from '@/components/auth-guard'
import './globals.css'

export const metadata: Metadata = {
  title: 'Pearson Spectre - AI Contract Compliance',
  description: 'Autonomous AI contract compliance copilot for Indian startups',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="font-sans antialiased bg-[#070912]">
        <AuthGuard>{children}</AuthGuard>
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
