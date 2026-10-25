import React from 'react';
import { SlideLayout } from '../SlideLayout';
import { Card } from '../Card';

export const Slide3Solution: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  const steps = [
    {
      num: '01',
      title: 'Funds Locked in Escrow',
      desc: "Client's budget is locked in a Solana escrow PDA before provider mobilizes. Provider has verifiable proof funds exist.",
      badge: 'TASK CREATION',
    },
    {
      num: '02',
      title: 'Work Verified & Approved',
      desc: 'Provider completes task and uploads proof. Client reviews, approves, and marks the contract fulfilled.',
      badge: 'SETTLEMENT GATE',
    },
    {
      num: '03',
      title: 'Automated Payout Release',
      desc: 'Smart contract automatically releases USDC payout to provider. In disputes, admin mediates with custom on-chain splits.',
      badge: 'TRUSTLESS PAYOUT',
    },
  ];

  return (
    <SlideLayout
      variant="light"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="ESCROW-POWERED SERVICES"
      headline="Make Every Transaction Trustless."
      summary="Blockchain settles the transaction cryptographically. Ordinary users never see a wallet or private key."
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px',
        }}
      >
        {steps.map((s, idx) => (
          <Card
            key={idx}
            variant="light"
            number={s.num}
            title={s.title}
            description={s.desc}
            badge={s.badge}
            badgeVariant="orange"
            index={idx}
          />
        ))}
      </div>
    </SlideLayout>
  );
};
