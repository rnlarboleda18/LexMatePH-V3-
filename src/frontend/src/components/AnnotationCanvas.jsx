import { useRef, useEffect } from 'react';

/**
 * AnnotationCanvas — transparent ink layer over topic content.
 *
 * ARCHITECTURE: OffscreenCanvas + Web Worker
 * All canvas drawing runs on a dedicated Worker thread (drawing-worker.js),
 * completely isolated from React, garbage collection, and other main-thread
 * work. The main thread only handles:
 *   - Pointer event receipt + coordinate math
 *   - postMessage to worker (draw, scroll, resize, undo/redo sync)
 *   - CSS positioning of the canvas element
 *
 * This means GC pauses and React re-renders cannot jank stroke rendering.
 * Combined with pointerrawupdate (fires before Chrome's event coalescing),
 * this gives the minimum achievable latency for a web-based canvas app.
 *
 * COORDINATE SYSTEM:
 * Strokes are stored in CONTENT-ABSOLUTE physical-pixel coordinates:
 *   cx = (clientX − rect.left)             × dpr
 *   cy = (clientY − rect.top + scrollTop)  × dpr
 *
 * The worker translates back to canvas-viewport coords on render:
 *   canvasY = contentY − scrollTop × dpr
 *
 * SCROLL: canvas.style.transform = translateY(scrollTop) keeps the canvas
 * aligned with the visible area without triggering layout.
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
  const canvasRef    = useRef(null);
  const workerRef    = useRef(null);
  const isDrawing    = useRef(false);

  // Cached canvas rect (updated at pointerdown + resize, never in move handler)
  const cachedRectRef = useRef(null);
  // Current scroll offset in CSS pixels
  const scrollTopRef  = useRef(0);
  // rAF handle for batching scroll redraws
  const scrollRafRef  = useRef(null);
  // Current DPR (updated on resize, read in event handlers)
  const dprRef        = useRef(Math.min(window.devicePixelRatio || 1, 3));

  // ── All mutable props mirrored to refs (event listeners registered once) ───
  const isAnnotatingRef     = useRef(isAnnotating);
  const currentToolRef      = useRef(currentTool);
  const penColorRef         = useRef(penColor);
  const highlighterColorRef = useRef(highlighterColor);
  const currentWidthRef     = useRef(currentWidth);
  const eraserWidthRef      = useRef(eraserWidth);
  const allowTouchDrawRef   = useRef(allowTouchDraw);
  const onStrokeCompleteRef = useRef(onStrokeComplete);

  useEffect(() => { isAnnotatingRef.current     = isAnnotating;     }, [isAnnotating]);
  useEffect(() => { currentToolRef.current      = currentTool;      }, [currentTool]);
  useEffect(() => { penColorRef.current         = penColor;         }, [penColor]);
  useEffect(() => { highlighterColorRef.current = highlighterColor; }, [highlighterColor]);
  useEffect(() => { currentWidthRef.current     = currentWidth;     }, [currentWidth]);
  useEffect(() => { eraserWidthRef.current      = eraserWidth;      }, [eraserWidth]);
  useEffect(() => { allowTouchDrawRef.current   = allowTouchDraw;   }, [allowTouchDraw]);
  useEffect(() => { onStrokeCompleteRef.current = onStrokeComplete; }, [onStrokeComplete]);

  // ── Worker creation + OffscreenCanvas transfer ───────────────────────────
  useEffect(() => {
    const canvas    = canvasRef.current;
    const container = scrollContainerRef?.current;
    if (!canvas || !container) return;

    // Spin up the drawing worker
    const worker = new Worker(
      new URL('../workers/drawing-worker.js', import.meta.url),
      { type: 'module' },
    );
    workerRef.current = worker;

    // Completed strokes come back from the worker
    worker.onmessage = ({ data }) => {
      if (data.type === 'stroke_complete') {
        onStrokeCompleteRef.current?.(data.stroke);
      }
    };

    // Transfer canvas pixel control to the worker — from this point the main
    // thread can still read/write canvas.style.* and getBoundingClientRect()
    // but canvas drawing APIs are exclusively owned by the worker.
    const dpr  = Math.min(window.devicePixelRatio || 1, 3);
    dprRef.current = dpr;
    const cssW = container.clientWidth  || 300;
    const cssH = container.clientHeight || 300;
    canvas.style.width  = cssW + 'px';
    canvas.style.height = cssH + 'px';
    cachedRectRef.current = canvas.getBoundingClientRect();

    const offscreen = canvas.transferControlToOffscreen();
    worker.postMessage(
      { type: 'init', canvas: offscreen,
        physicalWidth: cssW * dpr, physicalHeight: cssH * dpr, cssWidth: cssW },
      [offscreen],
    );

    // ResizeObserver keeps CSS dimensions and worker canvas in sync
    const sendResize = () => {
      const d = Math.min(window.devicePixelRatio || 1, 3);
      dprRef.current = d;
      const w = container.clientWidth  || 300;
      const h = container.clientHeight || 300;
      canvas.style.width  = w + 'px';
      canvas.style.height = h + 'px';
      cachedRectRef.current = canvas.getBoundingClientRect();
      worker.postMessage({ type: 'resize',
        physicalWidth: w * d, physicalHeight: h * d, cssWidth: w });
    };

    const ro = new ResizeObserver(sendResize);
    ro.observe(container);

    return () => {
      ro.disconnect();
      worker.terminate();
      workerRef.current = null;
    };
  }, [scrollContainerRef]);

  // ── Sync strokes to worker (undo / redo / load) ──────────────────────────
  useEffect(() => {
    workerRef.current?.postMessage({
      type: 'redraw', strokes, scrollTop: scrollTopRef.current,
    });
  }, [strokes]);

  // ── Clear on topic change ────────────────────────────────────────────────
  useEffect(() => {
    isDrawing.current = false;
    workerRef.current?.postMessage({ type: 'clear' });
    if (scrollRafRef.current) {
      cancelAnimationFrame(scrollRafRef.current);
      scrollRafRef.current = null;
    }
  }, [topicId]);

  // ── Cancel in-progress stroke when annotation mode turns off ────────────
  useEffect(() => {
    if (!isAnnotating) {
      isDrawing.current = false;
      workerRef.current?.postMessage({ type: 'stroke_cancel' });
      if (scrollRafRef.current) {
        cancelAnimationFrame(scrollRafRef.current);
        scrollRafRef.current = null;
      }
    }
  }, [isAnnotating]);

  // ── Pointer + scroll event listeners ────────────────────────────────────
  useEffect(() => {
    const canvas    = canvasRef.current;
    const container = scrollContainerRef?.current;
    if (!canvas || !container) return;

    function shouldDraw(e) {
      if (e.pointerType === 'pen')   return true;
      if (e.pointerType === 'mouse') return true;
      if (e.pointerType === 'touch') return allowTouchDrawRef.current;
      return false;
    }

    // Convert client coords → content-absolute physical-pixel coords.
    // All arithmetic runs on the main thread; the result is posted to the worker.
    function toContent(clientX, clientY) {
      const rect = cachedRectRef.current;
      if (!rect) return [0, 0];
      const dpr = dprRef.current;
      return [
        (clientX - rect.left)                       * dpr,
        (clientY - rect.top + scrollTopRef.current) * dpr,
      ];
    }

    // ── pointerdown ────────────────────────────────────────────────────────
    function onPointerDown(e) {
      if (!isAnnotatingRef.current) return;
      if (!shouldDraw(e))           return;
      if (!workerRef.current)       return;

      e.preventDefault();
      e.stopPropagation();
      try { canvas.setPointerCapture(e.pointerId); } catch (_) {}

      // Refresh rect once per stroke — the only getBoundingClientRect per stroke
      cachedRectRef.current = canvas.getBoundingClientRect();

      const isSPenEraser = e.pointerType === 'pen'
        && e.buttons === 32
        && /samsung/i.test(navigator.userAgent);
      const tool    = isSPenEraser ? 'eraser' : currentToolRef.current;
      const dpr     = dprRef.current;
      const baseW   = tool === 'eraser' ? eraserWidthRef.current : currentWidthRef.current;
      const width   = (tool === 'highlighter' ? baseW * 5 : baseW) * dpr;
      const opacity = tool === 'highlighter' ? 0.4 : 1.0;
      const color   = tool === 'pen'         ? penColorRef.current
                    : tool === 'highlighter' ? highlighterColorRef.current
                    : '#000000';
      const [cx, cy] = toContent(e.clientX, e.clientY);

      isDrawing.current = true;
      workerRef.current.postMessage({
        type: 'stroke_begin',
        id: crypto.randomUUID(),
        tool, color, width, opacity,
        cx, cy, pressure: e.pressure || 0.5,
      });
    }

    // ── Single-event draw — posts one position to the worker ──────────────
    function drawOneEvent(evt) {
      if (!workerRef.current) return;
      const rect = cachedRectRef.current;
      if (!rect) return;
      const dpr = dprRef.current;
      const st  = scrollTopRef.current;
      workerRef.current.postMessage({
        type: 'draw',
        cx:       (evt.clientX - rect.left)      * dpr,
        cy:       (evt.clientY - rect.top + st)  * dpr,
        pressure: evt.pressure || 0.5,
      });
    }

    // ── pointerrawupdate: pre-coalescing hardware-rate events ─────────────
    // On Chrome / Samsung Internet fires at S Pen hardware rate (~240 Hz)
    // BEFORE pointermove coalescing — earliest possible JS input latency.
    const supportsRawUpdate = 'onpointerrawupdate' in canvas;

    function onPointerRawUpdate(e) {
      if (!isDrawing.current)                  return;
      if (!isAnnotatingRef.current)            return;
      if (e.pointerType === 'touch'
        && !allowTouchDrawRef.current)         return;
      drawOneEvent(e);
    }

    // ── pointermove: kept for preventDefault (blocks Android scroll steal) ─
    // pointerrawupdate is non-cancelable, so pointermove is still needed here.
    // When pointerrawupdate is unavailable, also handles drawing as fallback.
    function onPointerMove(e) {
      if (!isDrawing.current)                  return;
      if (!isAnnotatingRef.current)            return;
      if (e.pointerType === 'touch'
        && !allowTouchDrawRef.current)         return;

      e.preventDefault();
      e.stopPropagation();

      if (supportsRawUpdate) return;

      // Fallback (Safari / Firefox)
      const events = typeof e.getCoalescedEvents === 'function'
        ? e.getCoalescedEvents() : [e];
      for (const evt of events) drawOneEvent(evt);
    }

    // ── pointerup ─────────────────────────────────────────────────────────
    function onPointerUp() {
      if (!isDrawing.current) return;
      isDrawing.current = false;
      workerRef.current?.postMessage({ type: 'stroke_end' });
      // Worker sends back { type:'stroke_complete', stroke } → onStrokeCompleteRef
    }

    function onPointerCancel() {
      isDrawing.current = false;
      workerRef.current?.postMessage({ type: 'stroke_cancel' });
    }

    // ── Scroll: reposition canvas via transform, redraw via worker ─────────
    function onScroll() {
      const st = container.scrollTop;
      scrollTopRef.current = st;
      // CSS transform: compositor thread only, zero layout cost
      canvas.style.transform = `translateY(${st}px)`;
      // Batch redraws — avoid flooding the worker during fast scroll
      if (!scrollRafRef.current) {
        scrollRafRef.current = requestAnimationFrame(() => {
          scrollRafRef.current = null;
          workerRef.current?.postMessage({ type: 'scroll', scrollTop: st });
        });
      }
    }

    const pOpts = { passive: false };
    if (supportsRawUpdate) {
      canvas.addEventListener('pointerrawupdate', onPointerRawUpdate, { passive: true });
    }
    canvas.addEventListener('pointerdown',   onPointerDown,   pOpts);
    canvas.addEventListener('pointermove',   onPointerMove,   pOpts);
    canvas.addEventListener('pointerup',     onPointerUp,     pOpts);
    canvas.addEventListener('pointercancel', onPointerCancel, pOpts);
    container.addEventListener('scroll',     onScroll,        { passive: true });

    return () => {
      if (supportsRawUpdate) {
        canvas.removeEventListener('pointerrawupdate', onPointerRawUpdate);
      }
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
        top:           0,       // static; scroll offset applied via CSS transform
        left:          0,
        pointerEvents: isAnnotating ? 'auto' : 'none',
        zIndex:        10,
        cursor:        isAnnotating ? 'crosshair' : 'default',
        touchAction:   'none',
      }}
    />
  );
}
