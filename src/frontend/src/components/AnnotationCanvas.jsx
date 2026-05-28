import { useRef, useEffect } from 'react';

/**
 * AnnotationCanvas — transparent ink layer over topic content.
 *
 * KEY DESIGN:
 * - Native addEventListener({ passive: false }) so preventDefault() actually
 *   blocks Samsung/Android scroll stealing — React synthetic events are passive
 *   by default in React 17+ and cannot preventDefault() reliably.
 * - getBoundingClientRect-based coords (more reliable than offsetX/Y on Android).
 * - devicePixelRatio scaling so strokes are sharp on high-DPI screens (Samsung Tab).
 * - Canvas positioned inside the scroll container → scrolls with content,
 *   no coordinate math needed.
 *
 * Supports:
 *   S Pen / Apple Pencil : pointerType === 'pen', pressure 0–1
 *   Mouse                : always (desktop + testing)
 *   Finger               : only when allowTouchDraw = true (palm rejection default)
 *   S Pen eraser barrel  : buttons === 32 on Samsung devices
 */
export default function AnnotationCanvas({
  topicId,
  isAnnotating,
  currentTool,
  penColor,
  highlighterColor,
  currentWidth,
  allowTouchDraw,
  strokes,
  onStrokeComplete,
  scrollContainerRef,
}) {
  const canvasRef   = useRef(null);
  const ctxRef      = useRef(null);
  const isDrawing   = useRef(false);
  const currentPath = useRef(null);

  // ── Keep ALL mutable props in refs so the native event listeners (registered
  //    once, deps=[]) always read the latest values without stale closures. ───
  const isAnnotatingRef     = useRef(isAnnotating);
  const currentToolRef      = useRef(currentTool);
  const penColorRef         = useRef(penColor);
  const highlighterColorRef = useRef(highlighterColor);
  const currentWidthRef     = useRef(currentWidth);
  const allowTouchDrawRef   = useRef(allowTouchDraw);
  const onStrokeCompleteRef = useRef(onStrokeComplete);
  const strokesRef          = useRef(strokes);

  useEffect(() => { isAnnotatingRef.current     = isAnnotating;     }, [isAnnotating]);
  useEffect(() => { currentToolRef.current      = currentTool;      }, [currentTool]);
  useEffect(() => { penColorRef.current         = penColor;         }, [penColor]);
  useEffect(() => { highlighterColorRef.current = highlighterColor; }, [highlighterColor]);
  useEffect(() => { currentWidthRef.current     = currentWidth;     }, [currentWidth]);
  useEffect(() => { allowTouchDrawRef.current   = allowTouchDraw;   }, [allowTouchDraw]);
  useEffect(() => { onStrokeCompleteRef.current = onStrokeComplete; }, [onStrokeComplete]);
  useEffect(() => { strokesRef.current          = strokes;          }, [strokes]);

  // ── Canvas sizing: match scroll container full height, scaled for DPR ───────
  // devicePixelRatio (e.g. 2 on Samsung Tab) means CSS pixels ≠ physical pixels.
  // We multiply canvas attribute dimensions by DPR so each CSS pixel maps to
  // DPR×DPR physical pixels — this is what makes strokes sharp instead of blurry.
  useEffect(() => {
    const canvas    = canvasRef.current;
    const container = scrollContainerRef?.current;
    if (!canvas || !container) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const cssW = container.scrollWidth  || 300;
      const cssH = Math.min(container.scrollHeight || 150, 8000);
      canvas.width  = cssW * dpr;   // physical pixels
      canvas.height = cssH * dpr;
      ctxRef.current = canvas.getContext('2d');
      redrawAll(ctxRef.current, canvas, strokesRef.current);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(container);
    resize();
    return () => ro.disconnect();
  }, [scrollContainerRef]);

  // ── Full redraw when strokes prop changes (undo / redo / load) ─────────────
  useEffect(() => {
    const ctx    = ctxRef.current;
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    redrawAll(ctx, canvas, strokes);
  }, [strokes]);

  // ── Clear canvas when topic changes ────────────────────────────────────────
  useEffect(() => {
    const ctx    = ctxRef.current;
    const canvas = canvasRef.current;
    if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
    isDrawing.current   = false;
    currentPath.current = null;
  }, [topicId]);

  // ── Stop stroke when annotation mode turns off ─────────────────────────────
  useEffect(() => {
    if (!isAnnotating) {
      isDrawing.current   = false;
      currentPath.current = null;
    }
  }, [isAnnotating]);

  // ── Non-passive native event listeners (the critical Samsung fix) ──────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    function shouldDraw(e) {
      if (e.pointerType === 'pen')   return true;
      if (e.pointerType === 'mouse') return true;
      if (e.pointerType === 'touch') return allowTouchDrawRef.current;
      return false;
    }

    // Translate client coords → canvas physical pixel coords.
    // scaleX = canvas.width (physical) / rect.width (CSS) = devicePixelRatio.
    function getCoords(e) {
      const rect   = canvas.getBoundingClientRect();
      const scaleX = canvas.width  / (rect.width  || 1);
      const scaleY = canvas.height / (rect.height || 1);
      return [
        (e.clientX - rect.left) * scaleX,
        (e.clientY - rect.top)  * scaleY,
      ];
    }

    function onPointerDown(e) {
      if (!isAnnotatingRef.current) return;
      if (!shouldDraw(e))           return;
      if (!ctxRef.current)          return;

      e.preventDefault();
      e.stopPropagation();

      try { canvas.setPointerCapture(e.pointerId); } catch (_) {}

      const isSPenEraser = e.pointerType === 'pen'
        && e.buttons === 32
        && /samsung/i.test(navigator.userAgent);
      const tool = isSPenEraser ? 'eraser' : currentToolRef.current;

      const dpr     = window.devicePixelRatio || 1;
      const [x, y]  = getCoords(e);
      const baseW   = currentWidthRef.current;

      isDrawing.current   = true;
      currentPath.current = {
        id:      crypto.randomUUID(),
        tool,
        // Stroke color comes from the per-tool color ref
        color:   tool === 'pen'
                   ? penColorRef.current
                   : tool === 'highlighter'
                     ? highlighterColorRef.current
                     : '#000000',
        // Store width in physical pixels so DPR is baked in once
        width:   tool === 'highlighter'
                   ? baseW * 5 * dpr
                   : baseW * dpr,
        opacity: tool === 'highlighter' ? 0.35 : 1.0,
        points:  [[x, y, e.pressure || 0.5]],
      };
    }

    function onPointerMove(e) {
      if (!isDrawing.current)           return;
      if (!isAnnotatingRef.current)     return;
      if (e.pointerType === 'touch'
        && !allowTouchDrawRef.current)  return;
      if (!ctxRef.current)              return;

      e.preventDefault();
      e.stopPropagation();

      const ctx      = ctxRef.current;
      const pts      = currentPath.current.points;
      const prev     = pts[pts.length - 1];
      const pressure = e.pressure || 0.5;
      const [x, y]   = getCoords(e);
      pts.push([x, y, pressure]);

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
      // stroke.width is already in physical pixels (baked with DPR on pointerdown)
      ctx.lineWidth = stroke.width * (0.5 + pressure * 1.5);
      ctx.beginPath();
      ctx.moveTo(prev[0], prev[1]);
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.restore();
    }

    function onPointerUp() {
      if (!isDrawing.current) return;
      isDrawing.current = false;

      const stroke        = currentPath.current;
      currentPath.current = null;

      if (stroke && stroke.points.length > 1) {
        onStrokeCompleteRef.current?.(stroke);
      }
    }

    function onPointerCancel() {
      isDrawing.current   = false;
      currentPath.current = null;
    }

    const opts = { passive: false };
    canvas.addEventListener('pointerdown',   onPointerDown,   opts);
    canvas.addEventListener('pointermove',   onPointerMove,   opts);
    canvas.addEventListener('pointerup',     onPointerUp,     opts);
    canvas.addEventListener('pointercancel', onPointerCancel, opts);

    return () => {
      canvas.removeEventListener('pointerdown',   onPointerDown);
      canvas.removeEventListener('pointermove',   onPointerMove);
      canvas.removeEventListener('pointerup',     onPointerUp);
      canvas.removeEventListener('pointercancel', onPointerCancel);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position:      'absolute',
        top:           0,
        left:          0,
        width:         '100%',
        pointerEvents: isAnnotating ? 'auto' : 'none',
        zIndex:        10,
        cursor:        isAnnotating ? 'crosshair' : 'default',
        touchAction:   'none',
      }}
    />
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function redrawAll(ctx, canvas, strokes) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  (strokes || []).forEach(s => drawStroke(ctx, s));
}

function drawStroke(ctx, stroke) {
  const pts = stroke.points;
  if (!pts || pts.length < 2) return;

  ctx.save();
  ctx.globalAlpha = stroke.opacity ?? 1.0;
  ctx.lineCap     = 'round';
  ctx.lineJoin    = 'round';

  if (stroke.tool === 'eraser') {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
  } else if (stroke.tool === 'highlighter') {
    ctx.globalCompositeOperation = 'multiply';
    ctx.strokeStyle = stroke.color ?? '#facc15';
  } else {
    ctx.globalCompositeOperation = 'source-over';
    ctx.strokeStyle = stroke.color ?? '#5b21b6';
  }

  for (let i = 1; i < pts.length; i++) {
    const pressure = pts[i][2] ?? 0.5;
    // stroke.width is stored in physical pixels (DPR already baked in at creation time)
    ctx.lineWidth  = (stroke.width ?? 2) * (0.5 + pressure * 1.5);
    ctx.beginPath();
    ctx.moveTo(pts[i - 1][0], pts[i - 1][1]);
    ctx.lineTo(pts[i][0],     pts[i][1]);
    ctx.stroke();
  }

  ctx.restore();
}
