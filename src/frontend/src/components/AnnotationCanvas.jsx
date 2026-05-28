import { useRef, useEffect } from 'react';

/**
 * AnnotationCanvas — transparent ink layer over topic content.
 *
 * PERFORMANCE DESIGN:
 * - getBoundingClientRect() cached at pointerdown (NOT per-move — layout reflow
 *   on every event is the #1 lag cause on Android/Samsung).
 * - requestAnimationFrame batching: pointer events accumulate in a ref and
 *   are flushed once per display frame → smooth even at 120 Hz S Pen rate.
 * - e.getCoalescedEvents(): recovers full 120 Hz S Pen sub-frame events that
 *   the browser would otherwise merge into one slower event.
 * - Canvas context state (composite op, strokeStyle, etc.) set once per frame
 *   batch, not per segment.
 * - devicePixelRatio scaling for crisp strokes on high-DPI screens.
 * - Non-passive native listeners so e.preventDefault() blocks Android scroll steal.
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

  // Cached canvas rect — updated at pointerdown + resize, NEVER in pointermove.
  const cachedRectRef     = useRef(null);

  // rAF batching
  const pendingSegsRef    = useRef([]);   // [{x0,y0,x1,y1,pressure}]
  const rafIdRef          = useRef(null);

  // ── All mutable props as refs (native listeners registered once, deps=[]) ───
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

  // ── Canvas sizing ────────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas    = canvasRef.current;
    const container = scrollContainerRef?.current;
    if (!canvas || !container) return;

    const resize = () => {
      const dpr  = Math.min(window.devicePixelRatio || 1, 3);
      const cssW = container.scrollWidth  || 300;
      const cssH = Math.min(container.scrollHeight || 150, 8000);
      canvas.width  = cssW * dpr;
      canvas.height = cssH * dpr;
      ctxRef.current = canvas.getContext('2d');
      // Refresh cached rect after resize
      cachedRectRef.current = canvas.getBoundingClientRect();
      redrawAll(ctxRef.current, canvas, strokesRef.current);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(container);
    resize();
    return () => ro.disconnect();
  }, [scrollContainerRef]);

  // ── Redraw when strokes change (undo / redo / load) ─────────────────────────
  useEffect(() => {
    const ctx    = ctxRef.current;
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    redrawAll(ctx, canvas, strokes);
  }, [strokes]);

  // ── Clear on topic change ────────────────────────────────────────────────────
  useEffect(() => {
    const ctx    = ctxRef.current;
    const canvas = canvasRef.current;
    if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
    isDrawing.current   = false;
    currentPath.current = null;
    if (rafIdRef.current) { cancelAnimationFrame(rafIdRef.current); rafIdRef.current = null; }
    pendingSegsRef.current = [];
  }, [topicId]);

  // ── Stop stroke when mode turns off ─────────────────────────────────────────
  useEffect(() => {
    if (!isAnnotating) {
      isDrawing.current   = false;
      currentPath.current = null;
      if (rafIdRef.current) { cancelAnimationFrame(rafIdRef.current); rafIdRef.current = null; }
      pendingSegsRef.current = [];
    }
  }, [isAnnotating]);

  // ── Non-passive native event listeners ──────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    function shouldDraw(e) {
      if (e.pointerType === 'pen')   return true;
      if (e.pointerType === 'mouse') return true;
      if (e.pointerType === 'touch') return allowTouchDrawRef.current;
      return false;
    }

    // Translate clientX/Y → canvas physical-pixel coords using the cached rect.
    // scaleX = canvas.width (physical) / rect.width (CSS) ≈ devicePixelRatio.
    // Called ONLY from pointerdown (to update pts[0]) and from the rAF flush;
    // the rect itself is only read from cache — no reflow.
    function clientToCanvas(clientX, clientY) {
      const rect   = cachedRectRef.current;
      if (!rect) return [0, 0];
      const scaleX = canvas.width  / (rect.width  || 1);
      const scaleY = canvas.height / (rect.height || 1);
      return [
        (clientX - rect.left) * scaleX,
        (clientY - rect.top)  * scaleY,
      ];
    }

    // rAF flush — draws all accumulated segments in one go.
    function flushPending() {
      rafIdRef.current = null;
      const segs   = pendingSegsRef.current;
      if (!segs.length || !isDrawing.current) return;
      pendingSegsRef.current = [];

      const ctx    = ctxRef.current;
      const stroke = currentPath.current;
      if (!ctx || !stroke) return;

      // Set context state ONCE per batch (not per segment — saves many API calls)
      ctx.globalAlpha = stroke.opacity;
      ctx.lineCap     = 'round';
      ctx.lineJoin    = 'round';
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

      for (const seg of segs) {
        ctx.lineWidth = stroke.width * (0.5 + seg.pressure * 1.5);
        ctx.beginPath();
        ctx.moveTo(seg.x0, seg.y0);
        ctx.lineTo(seg.x1, seg.y1);
        ctx.stroke();
      }

      // Reset blending state so redrawAll works cleanly
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }

    function onPointerDown(e) {
      if (!isAnnotatingRef.current) return;
      if (!shouldDraw(e))           return;
      if (!ctxRef.current)          return;

      e.preventDefault();
      e.stopPropagation();

      try { canvas.setPointerCapture(e.pointerId); } catch (_) {}

      // Refresh cached rect once at stroke start (cheap, only here)
      cachedRectRef.current = canvas.getBoundingClientRect();

      const isSPenEraser = e.pointerType === 'pen'
        && e.buttons === 32
        && /samsung/i.test(navigator.userAgent);
      const tool = isSPenEraser ? 'eraser' : currentToolRef.current;
      const dpr  = canvas.width / ((cachedRectRef.current?.width) || canvas.width);
      const baseW = currentWidthRef.current;

      const [x, y] = clientToCanvas(e.clientX, e.clientY);
      isDrawing.current   = true;
      currentPath.current = {
        id:      crypto.randomUUID(),
        tool,
        color:   tool === 'pen'         ? penColorRef.current
               : tool === 'highlighter' ? highlighterColorRef.current
               : '#000000',
        width:   (tool === 'highlighter' ? baseW * 5 : baseW) * dpr,
        opacity: tool === 'highlighter' ? 0.35 : 1.0,
        points:  [[x, y, e.pressure || 0.5]],
      };
    }

    function onPointerMove(e) {
      if (!isDrawing.current)          return;
      if (!isAnnotatingRef.current)    return;
      if (e.pointerType === 'touch'
        && !allowTouchDrawRef.current) return;

      e.preventDefault();
      e.stopPropagation();

      // getCoalescedEvents() recovers all sub-frame events at full pen rate
      // (e.g. 120 Hz S Pen → up to 2 events per 60 Hz display frame).
      const events = (typeof e.getCoalescedEvents === 'function')
        ? e.getCoalescedEvents()
        : [e];

      const pts = currentPath.current.points;
      for (const evt of events) {
        const pressure = evt.pressure || 0.5;
        const [x, y]   = clientToCanvas(evt.clientX, evt.clientY);
        const prev      = pts[pts.length - 1];
        pts.push([x, y, pressure]);
        pendingSegsRef.current.push({ x0: prev[0], y0: prev[1], x1: x, y1: y, pressure });
      }

      // Schedule exactly one draw per animation frame
      if (!rafIdRef.current) {
        rafIdRef.current = requestAnimationFrame(flushPending);
      }
    }

    function onPointerUp() {
      if (!isDrawing.current) return;

      // Flush any remaining segments before finalising
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
      flushPending();

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
      if (rafIdRef.current) { cancelAnimationFrame(rafIdRef.current); rafIdRef.current = null; }
      pendingSegsRef.current = [];
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
    ctx.lineWidth  = (stroke.width ?? 2) * (0.5 + pressure * 1.5);
    ctx.beginPath();
    ctx.moveTo(pts[i - 1][0], pts[i - 1][1]);
    ctx.lineTo(pts[i][0],     pts[i][1]);
    ctx.stroke();
  }

  // Reset
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
}
