import React from 'react';
import { SlideLayout } from '../SlideLayout';
import { Card } from '../Card';

export const Slide4HowItWorks: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  const zones = [
    {
      num: '01',
      zone: 'CLIENT EXPERIENCE',
      title: 'Post & Fund in Naira',
      desc: 'Client posts a task with budget and location radius. Pays instantly via Nigerian debit card or instant bank transfer.',
      details: 'No seed phrases. No crypto onboarding. Fiat-first simplicity.',
      badge: 'NAIRA RAILS',
      badgeVariant: 'slate' as const,
    },
    {
      num: '02',
      zone: 'REACH INFRASTRUCTURE',
      title: 'Escrow & Matchmaking',
      desc: 'Server-side relayer signs and deposits USDC into Solana PDA. PostGIS engine alerts verified nearby specialists.',
      details: 'Dual-custody float management with Obiex & FossaPay integration.',
      badge: 'CUSTODIAL RELAYER',
      badgeVariant: 'orange' as const,
    },
    {
      num: '03',
      zone: 'PROVIDER EXPERIENCE',
      title: 'Work, Deliver & Cash Out',
      desc: 'Provider accepts task, requests optional advance for materials, completes work, and receives instant payment.',
      details: 'Receives USDC directly or off-ramps straight to Nigerian bank accounts.',
      badge: 'USDC / NGN OFFRAMP',
      badgeVariant: 'slate' as const,
    },
  ];

  return (
    <SlideLayout
      variant="light"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="HOW REACH WORKS"
      headline="Simple for Users. Powerful Underneath."
      summary="Three funding rails: Naira cards, bank transfers, or native Solana wallet (Phantom / Solflare)."
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px',
        }}
      >
        {zones.map((z, idx) => (
          <Card
            key={idx}
            variant="light"
            number={z.num}
            title={z.title}
            description={z.desc}
            badge={z.badge}
            badgeVariant={z.badgeVariant}
            index={idx}
          >
            <div
              style={{
                marginTop: '16px',
                paddingTop: '12px',
                borderTop: '1px solid #f1f5f9',
                fontSize: '12.5px',
                color: '#64748b',
                fontStyle: 'italic',
              }}
            >
              {z.details}
            </div>
          </Card>
        ))}
      </div>
    </SlideLayout>
  );
};
