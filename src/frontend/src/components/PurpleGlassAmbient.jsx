import React from 'react';

/**
 * Page wrapper only (no frosted orbs). Subject / digest colors come from `colors.js`.
 */
export default function PurpleGlassAmbient({ children, className = '' }) {
  return <div className={`relative ${className}`.trim()}>{children}</div>;
}
