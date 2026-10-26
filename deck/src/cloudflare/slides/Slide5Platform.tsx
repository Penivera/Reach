import React from 'react';
import { SlideLayout } from '../SlideLayout';
import { Card } from '../Card';

export const Slide5Platform: React.FC<{ slideNumber: number; totalSlides: number }> = ({
  slideNumber,
  totalSlides,
}) => {
  const features = [
    {
      num: '01',
      title: 'Geospatial Matching',
      desc: 'PostGIS-powered engine matches tasks with verified providers within dynamic km radiuses.',
    },
    {
      num: '02',
      title: 'On-Chain Escrow',
      desc: 'Solana Anchor program handling collateral deposits, upfront advances, and automated release.',
    },
    {
      num: '03',
      title: 'Fiat Payment Rails',
      desc: 'Native integration with Obiex and FossaPay for local card checkout and bank off-ramps.',
    },
    {
      num: '04',
      title: 'Real-Time Messaging',
      desc: 'In-app client-provider chat for instant coordination, media sharing, and milestone updates.',
    },
    {
      num: '05',
      title: 'Reputation System',
      desc: 'Bidirectional reviews and verified completion metrics building permanent on-chain trust.',
    },
    {
      num: '06',
      title: 'Identity & KYC',
      desc: 'National Identity Number (NIN) and Bank Verification Number (BVN) checks via automated APIs.',
    },
  ];

  return (
    <SlideLayout
      variant="light"
      slideNumber={slideNumber}
      totalSlides={totalSlides}
      kicker="THE PLATFORM"
      headline="What We've Built."
      summary="PWA-ready. Push notifications via Firebase. Cloudinary media pipeline. Production engineering."
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '16px',
        }}
      >
        {features.map((f, idx) => (
          <Card
            key={idx}
            variant="light"
            number={f.num}
            title={f.title}
            description={f.desc}
            index={idx}
          />
        ))}
      </div>
    </SlideLayout>
  );
};
