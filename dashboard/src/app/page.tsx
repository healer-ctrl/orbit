import StatsCards from '@/components/StatsCards';
import EmailFeed from '@/components/EmailFeed';
import RiskGauge from '@/components/RiskGauge';
import ApprovalQueue from '@/components/ApprovalQueue';
import AgentPipeline from '@/components/AgentPipeline';
import DemoButton from '@/components/DemoButton';
import AuditTrail from '@/components/AuditTrail';

export default function Home() {
  return (
    <>
      <StatsCards />
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        <div className="lg:col-span-2">
          <EmailFeed />
        </div>
        
        <div className="lg:col-span-1 flex flex-col gap-6">
          <RiskGauge score={0.42} />
          <ApprovalQueue />
        </div>
      </div>
      
      <AgentPipeline />
      
      <div className="mt-8">
        <AuditTrail />
      </div>
      
      <DemoButton />
    </>
  );
}
