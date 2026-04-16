import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'StockSense',
  description: 'India Geopolitical Intelligence Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          padding: 0,
          background: "#080A0E",
          color: "#EDE8DC",
          fontFamily: "Instrument Sans",
        }}
      >
        {children}
      </body>
    </html>
  )
}