'use client';

import React from 'react';
import { Mail, CheckCircle, AlertTriangle, Activity } from 'lucide-react';

export default function StatsCards() {
  const stats = [
    { 
      label: 'Total Emails Processed', 
      value: '24,592', 
      icon: <Mail className="text-blue-500" size={24} />,
      subtext: '+12% from last week',
      color: 'blue'
    },
    { 
      label: 'Auto-Executed Actions', 
      value: '18,430', 
      icon: <CheckCircle className="text-green-500" size={24} />,
      subtext: '75% of total',
      color: 'green'
    },
    { 
      label: 'Pending Approvals', 
      value: '42', 
      icon: <AlertTriangle className="text-amber-500" size={24} />,
      subtext: 'Requires attention',
      color: 'amber'
    },
    { 
      label: 'Average Risk Score', 
      value: '18%', 
      icon: <Activity className="text-purple-500" size={24} />,
      subtext: 'Low risk overall',
      color: 'purple',
      bar: true
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {stats.map((stat, idx) => (
        <div key={idx} className="bg-[#1a2332] border border-[#2d3748] rounded-xl p-6 card-glow">
          <div className="flex justify-between items-start mb-4">
            <div className="text-[#94a3b8] font-medium text-sm">{stat.label}</div>
            <div className={`p-2 rounded-lg bg-${stat.color}-500/10`}>
              {stat.icon}
            </div>
          </div>
          <div className="text-3xl font-bold text-white mb-2">{stat.value}</div>
          
          {stat.bar ? (
            <div className="w-full bg-[#0a0f1c] rounded-full h-1.5 mt-3 mb-1">
              <div className="bg-gradient-to-r from-green-500 to-purple-500 h-1.5 rounded-full" style={{ width: '18%' }}></div>
            </div>
          ) : null}
          
          <div className="text-xs text-[#94a3b8]">{stat.subtext}</div>
        </div>
      ))}
    </div>
  );
}
