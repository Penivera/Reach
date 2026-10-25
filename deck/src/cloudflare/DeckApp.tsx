import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { Slide1Cover } from './slides/Slide1Cover';
import { Slide2Problem } from './slides/Slide2Problem';
import { Slide3Solution } from './slides/Slide3Solution';
import { Slide4HowItWorks } from './slides/Slide4HowItWorks';
import { Slide5Platform } from './slides/Slide5Platform';
import { Slide6Market } from './slides/Slide6Market';
import { Slide7Revenue } from './slides/Slide7Revenue';
import { Slide8Architecture } from './slides/Slide8Architecture';
import { Slide9Roadmap } from './slides/Slide9Roadmap';
import { Slide10Closing } from './slides/Slide10Closing';
import './deck.css';

interface SlideItem {
  id: string;
  name: string;
  component: React.ComponentType<{ slideNumber: number; totalSlides: number }>;
  notes: string;
  variant: 'dark' | 'light';
}

const SLIDES: SlideItem[] = [
  {
    id: 's1',
    name: 'Cover',
    component: Slide1Cover,
    notes: 'Open cold. Name the company and the product. Pause on REACH.',
    variant: 'dark',
  },
  {
    id: 's2',
    name: 'The Trust Gap',
    component: Slide2Problem,
    notes: 'Frame the pain: providers and clients both carry risk. The status quo has no guarantees.',
    variant: 'light',
  },
  {
    id: 's3',
    name: 'Solution',
    component: Slide3Solution,
    notes: 'Three steps. The user never sees the chain — they just feel the guarantee.',
    variant: 'light',
  },
  {
    id: 's4',
    name: 'How Reach Works',
    component: Slide4HowItWorks,
    notes: 'Three zones. The middle zone is where Reach earns its keep — escrow plus geospatial matching.',
    variant: 'light',
  },
  {
    id: 's5',
    name: 'The Platform',
    component: Slide5Platform,
    notes: 'Six features, shipped. Emphasize this is production code, not a prototype.',
    variant: 'light',
  },
  {
    id: 's6',
    name: 'Market Opportunity',
    component: Slide6Market,
    notes: 'The market is young, mobile-first, and crypto-fluent. Akwa Ibom (Uyo) first, then the region.',
    variant: 'light',
  },
  {
    id: 's7',
    name: 'Revenue Model',
    component: Slide7Revenue,
    notes: 'Three streams, all on-chain and auditable. Revenue is protocol infrastructure, not an opaque ledger.',
    variant: 'light',
  },
  {
    id: 's8',
    name: 'Architecture',
    component: Slide8Architecture,
    notes: 'Five layers, all production. Emphasize the server-side Solana relayer — users never touch keys.',
    variant: 'dark',
  },
  {
    id: 's9',
    name: 'Roadmap',
    component: Slide9Roadmap,
    notes: "Backend is built, contract is audited. We're closing the last mile to market.",
    variant: 'light',
  },
  {
    id: 's10',
    name: 'Closing',
    component: Slide10Closing,
    notes: 'Close on the three-word promise. Leave the contact on screen.',
    variant: 'dark',
  },
];

const getInitialSlide = (total: number) => {
  if (typeof window !== 'undefined') {
    const hash = window.location.hash.replace('#', '');
    const num = parseInt(hash, 10);
    if (!isNaN(num) && num >= 1 && num <= total) {
      return num - 1;
    }
  }
  return 0;
};

export const DeckApp: React.FC = () => {
  const total = SLIDES.length;
  const [current, setCurrent] = useState<number>(() => getInitialSlide(total));
  const [showNotes, setShowNotes] = useState<boolean>(false);
  const [showGrid, setShowGrid] = useState<boolean>(false);
  const shouldReduceMotion = useReducedMotion();

  const next = useCallback(() => {
    setCurrent((c) => Math.min(c + 1, total - 1));
  }, [total]);

  const prev = useCallback(() => {
    setCurrent((c) => Math.max(c - 1, 0));
  }, []);

  const goTo = useCallback(
    (index: number) => {
      if (index >= 0 && index < total) {
        setCurrent(index);
        setShowGrid(false);
      }
    },
    [total]
  );

  // Sync hash with current slide
  useEffect(() => {
    window.location.hash = `#${current + 1}`;
  }, [current]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Do not capture if typing inside input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (e.key) {
        case 'ArrowRight':
        case 'PageDown':
        case ' ':
          e.preventDefault();
          next();
          break;
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault();
          prev();
          break;
        case 'n':
        case 'N':
          setShowNotes((s) => !s);
          break;
        case 'g':
        case 'G':
          setShowGrid((s) => !s);
          break;
        case 'Escape':
          if (showGrid) setShowGrid(false);
          if (showNotes) setShowNotes(false);
          break;
        case 'f':
        case 'F':
          if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => {});
          } else {
            document.exitFullscreen().catch(() => {});
          }
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [next, prev, showGrid, showNotes]);

  // Screen click navigation
  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // Ignore clicks if clicking on interactive elements
    const target = e.target as HTMLElement;
    if (
      target.closest('a') ||
      target.closest('button') ||
      target.closest('.cf-notes-drawer') ||
      target.closest('.cf-grid-modal')
    ) {
      return;
    }

    const { clientX, currentTarget } = e;
    const { width } = currentTarget.getBoundingClientRect();
    if (clientX < width * 0.3) {
      prev();
    } else {
      next();
    }
  };

  const activeSlide = SLIDES[current];
  const ActiveComponent = activeSlide.component;

  return (
    <div className="cf-deck-root" onClick={handleClick}>
      {/* Active Slide with 200ms Cross-Fade Transition */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeSlide.id}
          style={{ width: '100%', height: '100%' }}
          initial={shouldReduceMotion ? { opacity: 1 } : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={shouldReduceMotion ? { opacity: 1 } : { opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
        >
          <ActiveComponent slideNumber={current + 1} totalSlides={total} />
        </motion.div>
      </AnimatePresence>

      {/* Speaker Notes Drawer (Toggled via 'N') */}
      {showNotes && (
        <div className="cf-notes-drawer">
          <div>
            <span
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                color: '#ea580c',
                fontWeight: 700,
                marginRight: '12px',
                fontSize: '11px',
                textTransform: 'uppercase',
              }}
            >
              SPEAKER NOTE (SLIDE {current + 1})
            </span>
            <span>{activeSlide.notes}</span>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setShowNotes(false);
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Grid Overview Modal (Toggled via 'G' or 'Escape') */}
      {showGrid && (
        <div
          className="cf-grid-modal"
          onClick={(e) => {
            e.stopPropagation();
            setShowGrid(false);
          }}
        >
          {SLIDES.map((s, idx) => (
            <div
              key={s.id}
              className={`cf-grid-thumb ${idx === current ? 'active' : ''}`}
              style={{
                background: s.variant === 'dark' ? '#0f172a' : '#ffffff',
                color: s.variant === 'dark' ? '#ffffff' : '#0f172a',
              }}
              onClick={(e) => {
                e.stopPropagation();
                goTo(idx);
              }}
            >
              <div
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '11px',
                  fontWeight: 700,
                  color: '#ea580c',
                }}
              >
                0{idx + 1}
              </div>
              <div style={{ fontSize: '13px', fontWeight: 600 }}>{s.name}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
