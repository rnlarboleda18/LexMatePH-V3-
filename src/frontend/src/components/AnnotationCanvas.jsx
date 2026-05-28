import { useRef, useEffect } from 'react';

/**
 * AnnotationCanvas — transparent ink layer over topic content.
 *
 * ARCHITECTURE (viewport canvas):
 * Canvas covers only the VISIBLE area of the scroll container (clientHeight),
 * not the full scrollable content (scrollHeight). This keeps the canvas small
 * so DPR × 2 doesn't balloon to 16 000 physical px tall and cause GPU lag.
 *
 * Strokes are stored in CONTENT-ABSOLUTE coordinates:
 *   contentY = (clientY − containerTop + scrollTop) × dpr
 *
 * On render, we translate back to canvas-viewport coordinates:
 *   canvasY = contentY − scrollTop × dpr
 *
 * On scroll the canvas `style.transform` is nudged via translateY(scrollTop)
 * so it always overlays the visible area. Using CSS transform instead of
 * style.top means repositioning happens on the compositor thread with zero
 * layout cost, and will-change:transform keeps the canvas on its own GPU
 * compositing layer for fast 2D drawing.
 *
 * HIGHLIGHTER — single-path rendering (critical):
 * Drawing each segment separately at globalAlpha=0.4 causes overlapping
 * segments to compound opacity and cover text. We fix this by drawing the
 * entire highlight stroke as ONE beginPath…stroke() call so the opacity is
 * applied exactly once across the full stroke extent.
 * During live drawing this means doing a full redrawAll + current stroke
 * on every rAF frame instead of incremental segment drawing.
 *
 * PERFORMANCE:
 * - getBoundingClientRect cached at pointerdown (no layout reflow per-move)
 * - requestAnimationFrame batches all pointermove segments into one draw call
 * - e.getCoalescedEvents() recovers full 120 Hz S Pen sub-frame events
 * - Non-passive listeners so e.preventDefault() blocks Android scroll steal
 * - devicePixelRatio applied for crisp strokes on high-DPI (Samsung Tab)
 * - CSS transform for scroll repositioning (compositor thread, no layout)
 * - will-change:transform promotes canvas to dedicated GPU compositing layer
 */
export default function AnnotationCanvas({
  topicId,
  isAnnotating,
  currentTool,
  penColor,
  highlighterColor,
  currentWidth,
  eraserWidth,
  allowTouchDraw,
  strokes,
  onStrokeComplete,
  scrollContainerRef,
}) {
  const canvasRef   = useRef(null);
  const ctxRef      = useRef(null);
  const isDrawing   = useRef(false);
  const currentPath = useRef(null);

  // Cached rect (only updated at pointerdown + resize, never in pointermove)
  const cachedRectRef  = useRef(null);
  // Current scroll offset in CSS pixels — updated by scroll handler
  const scrollTopRef   = useRef(0);

  // rAF handles
  const drawRafRef     = useRef(null);  // for live drawing batches
  const scrollRafRef   = useRef(null);  // for scroll re-renders
  const pendingSegsRef = useRef([]);

  // ── All mutable props as refs so native listeners (deps=[]) stay fresh ──────
  const isAnnotatingRef     = useRef(isAnnotating);
  const currentToolRef      = useRef(currentTool);
  const penColorRef         = useRef(penColor);
  const highlighterColorRef = useRef(highlighterColor);
  const currentWidthRef     = useRef(currentWidth);
  const eraserWidthRef      = useRef(eraserWidth);
  const allowTouchDrawRef   = useRef(allowTouchDraw);
  const onStrokeCompleteRef = useRef(onStrokeComplete);
  const strokesRef          = useRef(strokes);

  useEffect(() => { isAnnotatingRef.current     = isAnnotating;     }, [isAnnotating]);
  useEffect(() => { currentToolRef.current      = currentTool;      }, [currentTool]);
  useEffect(() => { penColorRef.current         = penColor;         }, [penColor]);
  useEffect(() => { highlighterColorRef.current = highlighterColor; }, [highlighterColor]);
  useEffect(() => { currentWidthRef.current     = currentWidth;     }, [currentWidth]);
  useEffect(() => { eraserWidthRef.current      = eraserWidth;      }, [eraserWidth]);
  useEffect(() => { allowTouchDrawRef.current   = allowTouchDraw;   }, [allowTouchDraw]);
  useEffect(() => { onStrokeCompleteRef.current = onStrokeComplete; }, [onStrokeComplete]);
  useEffect(() => { strokesRef.current          = strokes;          }, [strokes]);

  // ── Canvas sizing — VIEWPORT height only (not scrollHeight) ─────────────────
  useEffect(() => {
    const canvas    = canvasRef.current;
    const container = scrollContainerRef?.current;
    if (!canvas || !container) return;

    const resize = () => {
      const dpr  = Math.min(window.devicePixelRatio || 1, 3);
      const cssW = container.clientWidth  || 300;
      const cssH = container.clientHeight || 300;   // ← clientHeight, NOT scrollHeight
      canvas.width  = cssW * dpr;
      canvas.height = cssH * dpr;
      // CSS size matches the visible viewport
      canvas.style.width  = cssW + 'px';
      canvas.style.height = cssH + 'px';
      ctxRef.current = canvas.getContext('2d');
      cachedRectRef.current = canvas.getBoundingClientRect();
      redrawAll(ctxRef.current, canvas, strokesRef.current, scrollTopRef.current);
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
    redrawAll(ctx, canvas, strokes, scrollTopRef.current);
  }, [strokes]);

  // ── Clear on topic change ────────────────────────────────────────────────────
  useEffect(() => {
    const ctx    = ctxRef.current;
    const canvas = canvasRef.current;
    if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
    isDrawing.current   = false;
    currentPath.current = null;
    pendingSegsRef.current = [];
    if (drawRafRef.current)   { cancelAnimationFrame(drawRafRef.current);   drawRafRef.current   = null; }
    if (scrollRafRef.current) { cancelAnimationFrame(scrollRafRef.current); scrollRafRef.current = null; }
  }, [topicId]);

  // ── Stop stroke when mode turns off ─────────────────────────────────────────
  useEffect(() => {
    if (!isAnnotating) {
      isDrawing.current   = false;
      currentPath.current = null;
      pendingSegsRef.current = [];
      if (drawRafRef.current) { cancelAnimationFrame(drawRafRef.current); drawRafRef.current = null; }
    }
  }, [isAnnotating]);

  // ── Native event listeners (non-passive) + scroll handler ───────────────────
  useEffect(() => {
    const canvas    = canvasRef.current;
    const container = scrollContainerRef?.current;
    if (!canvas || !container) return;

    // ── Helpers ────────────────────────────────────────────────────────────────

    function shouldDraw(e) {
      if (e.pointerType === 'pen')   return true;
      if (e.pointerType === 'mouse') return true;
      if (e.pointerType === 'touch') return allowTouchDrawRef.current;
      return false;
    }

    // Effective DPR: ratio of physical canvas width to CSS width
    function getDpr() {
      const rect = cachedRectRef.current;
      return rect ? canvas.width / (rect.width || 1) : (window.devicePixelRatio || 1);
    }

    // Convert client coords → CONTENT-ABSOLUTE physical-pixel coords.
    // contentY includes scrollTop so strokes retain their position as user scrolls.
    function clientToContent(clientX, clientY) {
      const rect    = cachedRectRef.current;
      if (!rect) return [0, 0];
      const dpr     = getDpr();
      const scrollTop = scrollTopRef.current;
      return [
        (clientX - rect.left)                  * dpr,
        (clientY - rect.top  + scrollTop) * dpr,
      ];
    }

    // Convert content-absolute Y → canvas-viewport Y for rendering.
    function contentToCanvasY(contentY) {
      return contentY - scrollTopRef.current * getDpr();
    }

    // ── rAF flush: draw all pending segments in one go ─────────────────────────
    function flushPending() {
      drawRafRef.current = null;
      const segs  = pendingSegsRef.current;
      if (!segs.length || !isDrawing.current) return;
      pendingSegsRef.current = [];

      const ctx    = ctxRef.current;
      const stroke = currentPath.current;
      if (!ctx || !stroke) return;

      if (stroke.tool === 'highlighter') {
        // ── Highlighter: full redraw + single-path to prevent opacity stacking ─
        // Drawing segments at globalAlpha=0.4 individually compounds at overlaps
        // and makes the stroke fully opaque, covering text. Drawing as one path
        // applies the opacity only once across the entire stroke extent.
        redrawAll(ctx, canvas, strokesRef.current, scrollTopRef.current);
        const pts = stroke.points;
        if (pts.length >= 2) {
          const scrollPx = scrollTopRef.current * getDpr();
          ctx.save();
          ctx.globalAlpha              = stroke.opacity;
          ctx.globalCompositeOperation = 'source-over';
          ctx.strokeStyle              = stroke.color;
          ctx.lineCap                  = 'round';
          ctx.lineJoin                 = 'round';
          ctx.lineWidth                = stroke.width;  // fixed width; no pressure for highlighter
          ctx.beginPath();
          ctx.moveTo(pts[0][0], pts[0][1] - scrollPx);
          for (let i = 1; i < pts.length; i++) {
            ctx.lineTo(pts[i][0], pts[i][1] - scrollPx);
          }
          ctx.stroke();
          ctx.restore();
        }
      } else {
        // ── Pen / eraser: incremental segment draw (opacity = 1, no stacking) ─
        ctx.globalAlpha = stroke.opacity;
        ctx.lineCap     = 'round';
        ctx.lineJoin    = 'round';
        // Eraser must use destination-out to erase, not source-over
        ctx.globalCompositeOperation = stroke.tool === 'eraser' ? 'destination-out' : 'source-over';
        ctx.strokeStyle = stroke.tool === 'eraser' ? 'rgba(0,0,0,1)' : stroke.color;

        for (const seg of segs) {
          ctx.lineWidth = stroke.width * (0.5 + seg.pressure * 1.5);
          ctx.beginPath();
          ctx.moveTo(seg.x0, contentToCanvasY(seg.y0));
          ctx.lineTo(seg.x1, contentToCanvasY(seg.y1));
          ctx.stroke();
        }

        ctx.globalAlpha              = 1;
        ctx.globalCompositeOperation = 'source-over';
      }
    }

    // ── Pointer handlers ───────────────────────────────────────────────────────

    function onPointerDown(e) {
      if (!isAnnotatingRef.current) return;
      if (!shouldDraw(e))           return;
      if (!ctxRef.current)          return;

      e.preventDefault();
      e.stopPropagation();
      try { canvas.setPointerCapture(e.pointerId); } catch (_) {}

      // Refresh rect once per stroke (the only getBoundingClientRect call per stroke)
      cachedRectRef.current = canvas.getBoundingClientRect();

      const isSPenEraser = e.pointerType === 'pen'
        && e.buttons === 32
        && /samsung/i.test(navigator.userAgent);
      const tool  = isSPenEraser ? 'eraser' : currentToolRef.current;
      const dpr   = getDpr();
      // Eraser uses its own independent size setting
      const baseW = tool === 'eraser' ? eraserWidthRef.current : currentWidthRef.current;
      const [cx, cy] = clientToContent(e.clientX, e.clientY);

      isDrawing.current   = true;
      currentPath.current = {
        id:      crypto.randomUUID(),
        tool,
        color:   tool === 'pen'         ? penColorRef.current
               : tool === 'highlighter' ? highlighterColorRef.current
               : '#000000',
        // Width baked with DPR; highlighter is wider
        width:   (tool === 'highlighter' ? baseW * 5 : baseW) * dpr,
        // Highlighter uses partial opacity (source-over, NOT multiply)
        opacity: tool === 'highlighter' ? 0.4 : 1.0,
        points:  [[cx, cy, e.pressure || 0.5]],
      };
    }

    function onPointerMove(e) {
      if (!isDrawing.current)           return;
      if (!isAnnotatingRef.current)     return;
      if (e.pointerType === 'touch'
        && !allowTouchDrawRef.current)  return;

      e.preventDefault();
      e.stopPropagation();

      const pts    = currentPath.current.points;
      // getCoalescedEvents recovers full 120 Hz S Pen sub-frame input
      const events = (typeof e.getCoalescedEvents === 'function')
        ? e.getCoalescedEvents()
        : [e];

      for (const evt of events) {
        const pressure     = evt.pressure || 0.5;
        const [cx, cy]     = clientToContent(evt.clientX, evt.clientY);
        const prev         = pts[pts.length - 1];
        pts.push([cx, cy, pressure]);
        pendingSegsRef.current.push({
          x0: prev[0], y0: prev[1],
          x1: cx,      y1: cy,
          pressure,
        });
      }

      if (!drawRafRef.current) {
        drawRafRef.current = requestAnimationFrame(flushPending);
      }
    }

    function onPointerUp() {
      if (!isDrawing.current) return;

      // Flush remaining segments before committing
      if (drawRafRef.current) { cancelAnimationFrame(drawRafRef.current); drawRafRef.current = null; }
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
      pendingSegsRef.current = [];
      if (drawRafRef.current) { cancelAnimationFrame(drawRafRef.current); drawRafRef.current = null; }
    }

    // ── Scroll handler: reposition canvas via transform + re-render ────────────
    // Using CSS transform instead of style.top means repositioning happens on
    // the compositor thread with zero layout cost.
    function onScroll() {
      const st = container.scrollTop;
      scrollTopRef.current = st;
      // translateY keeps the canvas viewport-aligned without triggering layout
      canvas.style.transform = `translateY(${st}px)`;

      if (!scrollRafRef.current) {
        scrollRafRef.current = requestAnimationFrame(() => {
          scrollRafRef.current = null;
          redrawAll(ctxRef.current, canvasRef.current, strokesRef.current, scrollTopRef.current);
        });
      }
    }

    const pOpts = { passive: false };
    canvas.addEventListener('pointerdown',   onPointerDown,   pOpts);
    canvas.addEventListener('pointermove',   onPointerMove,   pOpts);
    canvas.addEventListener('pointerup',     onPointerUp,     pOpts);
    canvas.addEventListener('pointercancel', onPointerCancel, pOpts);
    container.addEventListener('scroll',     onScroll,        { passive: true });

    return () => {
      canvas.removeEventListener('pointerdown',   onPointerDown);
      canvas.removeEventListener('pointermove',   onPointerMove);
      canvas.removeEventListener('pointerup',     onPointerUp);
      canvas.removeEventListener('pointercancel', onPointerCancel);
      container.removeEventListener('scroll',     onScroll);
    };
  }, [scrollContainerRef]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <canvas
      ref={canvasRef}
      style={{
        position:      'absolute',
        top:           0,       // static; scroll offset applied via transform
        left:          0,
        // width + height set dynamically by resize effect
        pointerEvents: isAnnotating ? 'auto' : 'none',
        zIndex:        10,
        cursor:        isAnnotating ? 'crosshair' : 'default',
        touchAction:   'none',
      }}
    />
  );
}

// ── Rendering helpers ─────────────────────────────────────────────────────────

/**
 * Redraws all strokes onto the canvas, translating content-absolute Y coords
 * to canvas-viewport Y coords by subtracting scrollTop × dpr.
 */
function redrawAll(ctx, canvas, strokes, scrollTopCSS) {
  if (!ctx || !canvas) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const dpr        = canvas.width / (parseFloat(canvas.style.width) || canvas.width) || 1;
  const scrollPx   = (scrollTopCSS || 0) * dpr;   // scroll offset in physical pixels

  for (const stroke of (strokes || [])) {
    drawStroke(ctx, stroke, scrollPx);
  }
}

function drawStroke(ctx, stroke, scrollPx) {
  const pts = stroke.points;
  if (!pts || pts.length < 2) return;

  ctx.globalAlpha              = stroke.opacity ?? 1.0;
  ctx.globalCompositeOperation = stroke.tool === 'eraser' ? 'destination-out' : 'source-over';
  ctx.strokeStyle              = stroke.tool === 'eraser' ? 'rgba(0,0,0,1)' : (stroke.color ?? '#5b21b6');
  ctx.lineCap                  = 'round';
  ctx.lineJoin                 = 'round';

  if (stroke.tool === 'highlighter') {
    // ── Single path for the ENTIRE highlight stroke ────────────────────────
    // If we draw segment-by-segment at globalAlpha=0.4, every overlapping
    // endpoint compounds the opacity (0.4 + 0.4×0.6 + … → 1.0 after ~3 segs)
    // and the highlight becomes a solid, text-covering block.
    // Drawing as one continuous path applies globalAlpha exactly once.
    ctx.lineWidth = stroke.width ?? 2;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1] - scrollPx);
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i][0], pts[i][1] - scrollPx);
    }
    ctx.stroke();
  } else {
    // ── Pen / eraser: per-segment for pressure-sensitive width variation ───
    for (let i = 1; i < pts.length; i++) {
      const pressure = pts[i][2] ?? 0.5;
      ctx.lineWidth  = (stroke.width ?? 2) * (0.5 + pressure * 1.5);
      ctx.beginPath();
      ctx.moveTo(pts[i - 1][0],  pts[i - 1][1] - scrollPx);
      ctx.lineTo(pts[i][0],      pts[i][1]      - scrollPx);
      ctx.stroke();
    }
  }

  ctx.globalAlpha              = 1;
  ctx.globalCompositeOperation = 'source-over';
}
