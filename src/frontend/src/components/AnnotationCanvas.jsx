import React, { useRef, useEffect, useCallback } from 'react';

/**
 * AnnotationCanvas — transparent ink layer that floats over topic content.
 *
 * Placed *inside* the scroll container so it scrolls with content and
 * coordinates are always content-relative (no offset math needed).
 *
 * S Pen / Apple Pencil:  pointerType === 'pen', pressure 0–1
 * S Pen eraser barrel:   buttons === 32  (Samsung only)
 * Palm rejection:         pointerType === 'touch' ignored by default
 */
export default function AnnotationCanvas({
  topicId,
  isAnnotating,
  currentTool,        // 'pen' | 'highlighter' | 'eraser'
  currentColor,
  currentWidth,
  allowTouchDraw,     // allow finger drawing
  strokes,            // completed strokes from useAnnotations
  onStrokeComplete,   // fn(stroke) called when pointer is lifted
  scrollContainerRef, // ref to the scrollable wrapper div
}) {
  const canvasRef    = useRef(null);
  const ctxRef       = useRef(null);
  const isDrawing    = useRef(false);
  const currentPath  = useRef(null);

  // ── Canvas sizing: match scroll container's full content height ─────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = scrollContainerRef?.current;
    if (!canvas || !container) return;

    const resize = () => {
      const w = container.scrollWidth;
      const h = Math.min(container.scrollHeight, 8000); // iOS canvas limit guard
      if (canvas.width !== w || canvas.height !== h) {
        // Save current content before resize (resize clears canvas)
        canvas.width  = w;
        canvas.height = h;
        ctxRef.current = canvas.getContext('2d');
        redrawAll();
      }
    };

    const ro = new ResizeObserver(resize);
    ro.observe(container);
    resize(); // initial size

    return () => ro.disconnect();
  }, [scrollContainerRef, strokes]); // re-init when strokes change (for redraw after undo)

  // ── Full redraw whenever strokes prop changes (undo/redo/load) ──────────────
  const redrawAll = useCallback(() => {
    const ctx = ctxRef.current;
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    strokes.forEach(s => drawStroke(ctx, s));
  }, [strokes]);

  useEffect(() => {
    redrawAll();
  }, [strokes]);

  // ── Pointer event handlers ──────────────────────────────────────────────────
  const getEffectiveTool = (e) => {
    // Samsung S Pen eraser barrel: buttons === 32
    const isSPenEraser = e.pointerType === 'pen'
      && e.buttons === 32
      && /samsung/i.test(navigator.userAgent);
    return isSPenEraser ? 'eraser' : currentTool;
  };

  const shouldDraw = (e) => {
    if (e.pointerType === 'pen') return true;
    if (allowTouchDraw && e.pointerType === 'touch') return true;
    return false;
  };

  const handlePointerDown = useCallback((e) => {
    if (!isAnnotating) return;
    if (!shouldDraw(e)) return;

    const canvas = canvasRef.current;
    canvas.setPointerCapture(e.pointerId);

    const tool = getEffectiveTool(e);
    isDrawing.current = true;
    currentPath.current = {
      id:      crypto.randomUUID(),
      tool,
      color:   tool === 'eraser' ? '#000000' : currentColor,
      width:   tool === 'highlighter' ? currentWidth * 5 : currentWidth,
      opacity: tool === 'highlighter' ? 0.35 : 1.0,
      points:  [[e.offsetX, e.offsetY, e.pressure || 0.5]],
    };
    e.preventDefault();
  }, [isAnnotating, currentTool, currentColor, currentWidth, allowTouchDraw]);

  const handlePointerMove = useCallback((e) => {
    if (!isDrawing.current || !isAnnotating) return;
    if (!shouldDraw(e)) return;

    const ctx = ctxRef.current;
    if (!ctx) return;

    const pts = currentPath.current.points;
    const prev = pts[pts.length - 1];
    const pressure = e.pressure || 0.5;
    pts.push([e.offsetX, e.offsetY, pressure]);

    // Draw just the new segment live (fast, no full redraw)
    const stroke = currentPath.current;
    ctx.save();
    ctx.globalAlpha = stroke.opacity;
    if (stroke.tool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.strokeStyle = 'rgba(0,0,0,1)';
    } else if (stroke.tool === 'highlighter') {
      ctx.globalCompositeOperation = 'multiply';
      ctx.strokeStyle = stroke.color;
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = stroke.color;
    }
    ctx.lineCap   = 'round';
    ctx.lineJoin  = 'round';
    ctx.lineWidth = stroke.width * (0.5 + pressure * 1.5);
    ctx.beginPath();
    ctx.moveTo(prev[0], prev[1]);
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
    ctx.restore();
    e.preventDefault();
  }, [isAnnotating, allowTouchDraw]);

  const handlePointerUp = useCallback((e) => {
    if (!isDrawing.current) return;
    isDrawing.current = false;

    const stroke = currentPath.current;
    currentPath.current = null;

    if (stroke && stroke.points.length > 1) {
      onStrokeComplete?.(stroke);
      // onStrokeComplete triggers strokes prop update → redrawAll via useEffect
    }
  }, [onStrokeComplete]);

  const handlePointerCancel = useCallback(() => {
    isDrawing.current = false;
    currentPath.current = null;
  }, []);

  // ── When annotation mode turns off, stop any active stroke ─────────────────
  useEffect(() => {
    if (!isAnnotating) {
      isDrawing.current = false;
      currentPath.current = null;
    }
  }, [isAnnotating]);

  // ── Reset canvas when topic changes ────────────────────────────────────────
  useEffect(() => {
    const ctx = ctxRef.current;
    const canvas = canvasRef.current;
    if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
    isDrawing.current = false;
    currentPath.current = null;
  }, [topicId]);

  return (
    <canvas
      ref={canvasRef}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      style={{
        position:      'absolute',
        top:           0,
        left:          0,
        width:         '100%',
        pointerEvents: isAnnotating ? 'all' : 'none',
        zIndex:        10,
        cursor:        isAnnotating ? 'crosshair' : 'default',
        touchAction:   isAnnotating ? 'none' : 'auto',
      }}
    />
  );
}

// ── Stroke rendering helper ────────────────────────────────────────────────────

function drawStroke(ctx, stroke) {
  const pts = stroke.points;
  if (!pts || pts.length < 2) return;

  ctx.save();
  ctx.globalAlpha  = stroke.opacity ?? 1.0;
  ctx.lineCap      = 'round';
  ctx.lineJoin     = 'round';

  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
  } else if (stroke.tool === 'highlighter') {
    ctx.globalCompositeOperation = 'multiply';
    ctx.strokeStyle = stroke.color ?? '#ffff00';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = stroke.color ?? '#5b21b6';
  }

  for (let i = 1; i < pts.length; i++) {
    const pressure = pts[i][2] ?? 0.5;
    ctx.lineWidth  = (stroke.width ?? 2) * (0.5 + pressure * 1.5);
    ctx.beginPath();
    ctx.moveTo(pts[i - 1][0], pts[i - 1][1]);
    ctx.lineTo(pts[i][0],     pts[i][1]);
    ctx.stroke();
  }

  ctx.restore();
}
