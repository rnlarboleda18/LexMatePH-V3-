import { useVisualViewportCssVars } from '../hooks/useVisualViewportCssVars';

/**
 * Renders null; subscribes to `visualViewport` and syncs `documentElement` CSS vars for fixed shells.
 */
export function VisualViewportRoot() {
    useVisualViewportCssVars();
    return null;
}
