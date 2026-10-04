'use client';

import React from 'react';
import { Zap, Loader2, Sparkles } from 'lucide-react';

interface Props {
  isRunning: boolean;
  onTriggerDemo: () => void;
}

export default function DemoButton({ isRunning, onTriggerDemo }: Props) {
  return (
    <div className="fixed bottom-6 right-6 z-40">
      <button
        onClick={onTriggerDemo}
        disabled={isRunning}
        className="flex items-center gap-2.5 px-6 py-3.5 rounded-full font-bold text-sm text-white shadow-2xl transition-all transform hover:scale-105 active:scale-95 bg-gradient-to-r from-sky-500 via-indigo-600 to-purple-600 hover:shadow-[0_0_30px_rgba(56,189,248,0.5)] border border-white/20 disabled:opacity-75 disabled:cursor-not-allowed cursor-pointer"
      >
        {isRunning ? (
          <>
            <Loader2 className="animate-spin text-white" size={18} />
            <span>Processing Pipeline...</span>
          </>
        ) : (
          <>
            <Zap className="text-amber-300 fill-amber-300 animate-pulse" size={18} />
            <span>Simulate Live Inbound Emails</span>
          </>
        )}
      </button>
    </div>
  );
}
