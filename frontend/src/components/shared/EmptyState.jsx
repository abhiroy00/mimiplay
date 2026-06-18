import React from 'react';
import Button from './Button';
import { motion as Motion } from 'framer-motion';

const EmptyState = ({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  size = 'md'
}) => {
  const iconSize = size === 'sm' ? 32 : size === 'lg' ? 80 : 56;
  const containerClass = size === 'sm' ? 'py-4' : size === 'lg' ? 'py-16' : 'py-8';

  return (
    <Motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex flex-col items-center justify-center text-center ${containerClass}`}
    >
      {Icon && (
        <Motion.div
          animate={{ y: [0, -5, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="mb-4"
        >
          <Icon size={iconSize} className="text-primary-300" />
        </Motion.div>
      )}

      <h3 className={`font-bold text-text mb-2 ${size === 'sm' ? 'text-lg' : 'text-2xl'}`}>
        {title}
      </h3>

      <p className={`text-text/60 mb-4 ${size === 'sm' ? 'text-sm' : 'text-base'}`}>
        {description}
      </p>

      {onAction && actionLabel && (
        <Button variant="primary" size={size === 'sm' ? 'sm' : 'md'} onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </Motion.div>
  );
};

export default EmptyState;
