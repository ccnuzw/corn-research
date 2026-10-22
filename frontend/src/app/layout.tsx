import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import '@/styles/globals.css'
import { Toaster } from '@/components/ui/toaster'
import { ConfirmProvider } from '@/components/ui/confirm-dialog'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '玉米研究系统V2',
  description: '企业级玉米商品研究数据平台',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className={inter.className}>
        <ConfirmProvider>
          {children}
          <Toaster />
        </ConfirmProvider>
      </body>
    </html>
  )
}
