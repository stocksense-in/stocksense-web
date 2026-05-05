import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'StockSense — Intelligence, Not Luck',
  description: 'India Geopolitical Intelligence Platform — Real fundamentals, live geopolitics, institutional tools built for Indian retail investors.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  )
}