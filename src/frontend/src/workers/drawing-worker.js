/**
 * drawing-worker.js — OffscreenCanvas rendering thread for AnnotationCanvas.
 *
 * All canvas draw calls happen here, completely isolated from the React/JS
 * main thread. GC pauses, React re-renders, and other main-thread work cannot
 * block or jank stroke rendering.
 *
 * Message protocol  (main → worker):
 *   init         { canvas, physicalWidth, physicalHeight, cssWidth }
 *   resize       { physicalWidth, physicalHeight, cssWidth }
 *   redraw       { strokes, scrollTop? }
 *   scroll       { scrollTop }
 *   clear        {}
 *   stroke_begin { id, tool, color, width, opacity, cx, cy, pressure }
 *   draw         { cx, cy, pressure }   ← one per pointerrawupdate event
 *   stroke_end   {}
 *   stroke_cancel{}
 *
 * Message protocol  (worker → main):
 *   stroke_complete { stroke }
 */

let canvas        = null;
let ctx           = null;
let cssWidth      = 300;
let scrollTopCSS  = 0;
let strokes       = [];       // committed strokes synced from main thread
let currentStroke = null;     // in-progress stroke

// ── Helpers ───────────────────────────────────────────────────────────────────

function getDpr() {
  return (canvas && cssWidth) ? canvas.width / cssWidth : 1;
}

function sp() {   // current scroll offset in physical pixels
  return scrollTopCSS * getDpr();
}

// ── Stroke rendering ──────────────────────────────────────────────────────────

function drawStroke(stroke, scrollPx) {
  const pts = stroke.points;
  if (!pts || pts.length < 2) return;

  ctx.globalAlpha              = stroke.opacity ?? 1.0;
  ctx.globalCompositeOperation = stroke.tool === 'eraser' ? 'destination-out' : 'source-over';
  ctx.strokeStyle              = stroke.tool === 'eraser' ? 'rgba(0,0,0,1)' : (stroke.color ?? '#5b21b6');
  ctx.lineCap                  = 'round';
  ctx.lineJoin                 = 'round';

  if (stroke.tool === 'highlighter') {
    // Single continuous path — prevents opacity stacking at overlapping endpoints
    ctx.lineWidth = stroke.width ?? 2;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1] - scrollPx);
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i][0], pts[i][1] - scrollPx);
    }
    ctx.stroke();
  } else {
    // Per-segment for pressure-sensitive width variation
    for (let i = 1; i < pts.length; i++) {
      const pressure = pts[i][2] ?? 0.5;
      ctx.lineWidth  = (stroke.width ?? 2) * (0.5 + pressure * 1.5);
      ctx.beginPath();
      ctx.moveTo(pts[i - 1][0], pts[i - 1][1] - scrollPx);
      ctx.lineTo(pts[i][0],     pts[i][1]     - scrollPx);
      ctx.stroke();
    }
  }

  ctx.globalAlpha              = 1;
  ctx.globalCompositeOperation = 'source-over';
}

function redrawAll(scrollPx) {
  if (!ctx || !canvas) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  for (const s of strokes) drawStroke(s, scrollPx);
}

function drawCurrentHighlighter(scrollPx) {
  if (!currentStroke || currentStroke.points.length < 2) return;
  const pts = currentStroke.points;
  ctx.save();
  ctx.globalAlpha              = currentStroke.opacity;
  ctx.globalCompositeOperation = 'source-over';
  ctx.strokeStyle              = currentStroke.color;
  ctx.lineCap                  = 'round';
  ctx.lineJoin                 = 'round';
  ctx.lineWidth                = currentStroke.width;
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1] - scrollPx);
  for (let i = 1; i < pts.length; i++) {
    ctx.lineTo(pts[i][0], pts[i][1] - scrollPx);
  }
  ctx.stroke();
  ctx.restore();
}

// ── Message handler ───────────────────────────────────────────────────────────

self.onmessage = ({ data }) => {
  switch (data.type) {

    case 'init': {
      canvas        = data.canvas;
      canvas.width  = data.physicalWidth;
      canvas.height = data.physicalHeight;
      cssWidth      = data.cssWidth;
      ctx           = canvas.getContext('2d');
      break;
    }

    case 'resize': {
      canvas.width  = data.physicalWidth;
      canvas.height = data.physicalHeight;
      cssWidth      = data.cssWidth;
      ctx           = canvas.getContext('2d');
      redrawAll(sp());
      break;
    }

    case 'redraw': {
      strokes = data.strokes || [];
      if (data.scrollTop != null) scrollTopCSS = data.scrollTop;
      redrawAll(sp());
      break;
    }

    case 'scroll': {
      scrollTopCSS = data.scrollTop;
      redrawAll(sp());
      break;
    }

    case 'clear': {
      strokes       = [];
      currentStroke = null;
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      break;
    }

    case 'stroke_begin': {
      currentStroke = {
        id:      data.id,
        tool:    data.tool,
        color:   data.color,
        width:   data.width,
        opacity: data.opacity,
        points:  [[data.cx, data.cy, data.pressure]],
      };
      break;
    }

    case 'draw': {
      if (!currentStroke || !ctx) break;
      const pts      = currentStroke.points;
      const prev     = pts[pts.length - 1];
      const { cx, cy, pressure } = data;
      pts.push([cx, cy, pressure]);

      const scrollPx = sp();

      if (currentStroke.tool === 'highlighter') {
        // Full redraw + single path on every event to prevent opacity stacking.
        // Running on the worker thread so this doesn't block the main thread.
        redrawAll(scrollPx);
        drawCurrentHighlighter(scrollPx);
      } else {
        // Pen / eraser: draw segment immediately — zero latency
        ctx.globalAlpha              = currentStroke.opacity;
        ctx.lineCap                  = 'round';
        ctx.lineJoin                 = 'round';
        ctx.globalCompositeOperation = currentStroke.tool === 'eraser'
          ? 'destination-out' : 'source-over';
        ctx.strokeStyle = currentStroke.tool === 'eraser'
          ? 'rgba(0,0,0,1)' : currentStroke.color;
        ctx.lineWidth   = currentStroke.width * (0.5 + pressure * 1.5);
        ctx.beginPath();
        ctx.moveTo(prev[0], prev[1] - scrollPx);
        ctx.lineTo(cx,      cy      - scrollPx);
        ctx.stroke();
        ctx.globalAlpha              = 1;
        ctx.globalCompositeOperation = 'source-over';
      }
      break;
    }

    case 'stroke_end': {
      const stroke  = currentStroke;
      currentStroke = null;
      if (stroke && stroke.points.length > 1) {
        strokes.push(stroke);    // keep rendered while main thread persists it
        self.postMessage({ type: 'stroke_complete', stroke });
      }
      break;
    }

    case 'stroke_cancel': {
      currentStroke = null;
      redrawAll(sp());
      break;
    }
  }
};
