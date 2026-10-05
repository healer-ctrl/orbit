import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Sidebar from '@/components/Sidebar';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Orbit - Intelligent Financial Email Automation',
  description: 'AI-powered email classification, PII guardrails, and autonomous settlement for capital markets.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 ml-64 p-8 overflow-x-hidden">
            <header className="flex justify-between items-center mb-8 pb-4 border-b border-[#2d3748]">
              <div>
                <h1 className="text-2xl font-bold text-white">Dashboard</h1>
                <p className="text-[#94a3b8] text-sm mt-1">Intelligent Financial Email Automation</p>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="bg-[#1a2332] px-4 py-2 rounded-lg border border-[#2d3748] flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 pulse-dot"></div>
                  <span className="text-sm font-medium text-white">Live Monitoring Active</span>
                </div>
                
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold border-2 border-[#1a2332] shadow-lg">
                  OP
                </div>
              </div>
            </header>
            
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
