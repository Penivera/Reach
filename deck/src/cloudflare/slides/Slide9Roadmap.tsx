import React from 'react';
import { SlideLayout } from '../SlideLayout';
import { Card } from '../Card';

export const Slide9Roadmap: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  const milestones = [
    {
      quarter: 'Q3 2026',
      status: 'COMPLETE',
      statusVariant: 'green' as const,
      title: 'Backend & Contracts',
      desc: 'Solana Anchor program audited & patched. FastAPI relayer & treasury engine built with 158 tests passing.',
    },
    {
      quarter: 'Q4 2026',
      status: 'IN FLIGHT',
      statusVariant: 'orange' as const,
      title: 'Staging & Integration',
      desc: 'Finalizing checkout screens, wallet connection modals, and live Obiex business settlement tests.',
    },
    {
      quarter: 'Q1 2027',
      status: 'TARGET',
      statusVariant: 'slate' as const,
      title: 'Uyo Beta Launch',
      desc: 'Controlled beta release across Uyo commercial clusters. First 1,000 live escrow task settlements.',
    },
    {
      quarter: 'Q2 2027',
      status: 'TARGET',
      statusVariant: 'slate' as const,
      title: 'Multi-City Scale',
      desc: 'Physical trade items added. Expansion to Port Harcourt, Calabar, and Lagos.',
    },
    {
      quarter: 'Q3 2027',
      status: 'PLANNED',
      statusVariant: 'slate' as const,
      title: 'Multichain & Regional',
      desc: 'NEAR Intents cross-chain integration. Entering regional West African commercial centers (Accra).',
    },
  ];

  return (
    <SlideLayout
      variant="light"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="EXECUTION TIMELINE"
      headline="From Code to Market."
      summary="The backend is built. The smart contract is audited. We are closing the last mile to commercial launch."
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '14px',
        }}
      >
        {milestones.map((m, idx) => (
          <Card
            key={idx}
            variant="light"
            number={m.quarter}
            badge={m.status}
            badgeVariant={m.statusVariant}
            title={m.title}
            description={m.desc}
            index={idx}
          />
        ))}
      </div>
    </SlideLayout>
  );
};
