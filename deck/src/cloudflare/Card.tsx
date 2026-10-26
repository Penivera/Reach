import React, { type ReactNode } from 'react';
import { motion, useReducedMotion } from 'motion/react';

export interface CardProps {
  number?: string;
  icon?: ReactNode;
  title?: ReactNode;
  description?: ReactNode;
  badge?: string;
  badgeVariant?: 'orange' | 'green' | 'red' | 'slate';
  variant?: 'light' | 'dark';
  children?: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  index?: number;
}

export const Card: React.FC<CardProps> = ({
  number,
  icon,
  title,
  description,
  badge,
  badgeVariant = 'orange',
  variant = 'light',
  children,
  className = '',
  style,
  index = 0,
}) => {
  const shouldReduceMotion = useReducedMotion();

  const animationProps = shouldReduceMotion
    ? {}
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        transition: {
          duration: 0.3,
          delay: 0.06 * index,
          ease: [0.16, 1, 0.3, 1] as const,
        },
      };

  const isLight = variant === 'light';

  return (
    <motion.div
      className={`cf-card ${isLight ? 'cf-card-light' : 'cf-card-dark'} ${className}`}
      style={style}
      {...animationProps}
    >
      {(number || icon || badge) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {number && (
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '12px',
                  fontWeight: 700,
                  color: '#ea580c',
                  letterSpacing: '0.05em',
                }}
              >
                {number}
              </span>
            )}
            {icon && (
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: isLight ? '#f1f5f9' : '#334155',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ea580c',
                }}
              >
                {icon}
              </div>
            )}
          </div>
          {badge && (
            <span className={`cf-badge cf-badge-${badgeVariant}`}>{badge}</span>
          )}
        </div>
      )}

      {title && (
        <h3
          style={{
            fontSize: '17px',
            fontWeight: 700,
            letterSpacing: '-0.02em',
            margin: '0 0 6px 0',
            color: isLight ? '#0f172a' : '#ffffff',
            lineHeight: 1.3,
          }}
        >
          {title}
        </h3>
      )}

      {description && (
        <p
          style={{
            fontSize: '14px',
            color: isLight ? '#64748b' : '#94a3b8',
            lineHeight: 1.5,
            margin: 0,
          }}
        >
          {description}
        </p>
      )}

      {children}
    </motion.div>
  );
};
