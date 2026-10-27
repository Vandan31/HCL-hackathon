/**
 * COMPONENT : ui (landing decoration)
 * PURPOSE   : Small syllables of English, Hindi and Gujarati drifting slowly in 3D behind the language card.
 * INPUTS    : a <canvas> element; CONFIG.LANDING_GLYPHS / LANDING_GLYPH_COUNT
 * OUTPUTS   : animation on the canvas; startLanding3D() returns a stop() that frees the GPU
 * DEPENDS ON: src/ui/vendor/three/three.module.min.js (Three.js r170, MIT, saved locally so it works offline),
 *             config/ui.js
 * PANEL NOTE: Pure decoration, and optional: if Three.js or WebGL fails, the landing page simply looks plain;
 *             it is hidden from screen readers, still under "reduce motion", and shut down once a language is chosen.
 */

import { CONFIG } from "../../config/ui.js";

// Colours from the lemon theme (src/ui/styles.css): dark amber and ink, so the letters read as soft texture.
const COLORS = ["#7a5600", "#5c4a10", "#2b2200", "#b39200"];
const FONT = '"Nirmala UI", "Noto Sans Devanagari", "Noto Sans Gujarati", "Segoe UI", sans-serif';

const rand = (a, b) => a + Math.random() * (b - a);

/**
 * Draw one syllable onto a small 2D canvas and turn it into a texture.
 * WHY not Three.js 3D text: its text geometry can't shape Devanagari/Gujarati (conjuncts and vowel signs break);
 * the browser's own text drawing handles both scripts correctly.
 */
function glyphTexture(THREE, text, color) {
  const size = 128;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  ctx.fillStyle = color;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `600 ${text.length > 2 ? 52 : 72}px ${FONT}`;   // longer syllables ("क्ष", "Ya") a bit smaller to fit
  ctx.fillText(text, size / 2, size / 2 + 4);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

/**
 * Start the floating syllables on `canvas`. Returns stop(), or null if it couldn't start (no WebGL, script failed),
 * in which case the page stays exactly as it was.
 */
export async function startLanding3D(canvas) {
  let THREE;
  try {
    THREE = await import("./vendor/three/three.module.min.js");
  } catch (e) {
    return null;   // FALLBACK: library missing or blocked -> plain landing page
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  } catch (e) {
    return null;   // FALLBACK: no WebGL (old phone, disabled GPU) -> plain landing page
  }
  // WHY cap at 1.5: sharp enough for small letters, without making weak phones draw 3x the pixels.
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 50);
  camera.position.z = 10;
  const group = new THREE.Group();
  scene.add(group);

  // One texture per (syllable, colour) pair, shared by every sprite that uses it.
  const textures = new Map();
  const textureFor = (text, color) => {
    const key = `${text}|${color}`;
    if (!textures.has(key)) textures.set(key, glyphTexture(THREE, text, color));
    return textures.get(key);
  };

  const glyphs = CONFIG.LANDING_GLYPHS;
  const sprites = [];
  for (let i = 0; i < CONFIG.LANDING_GLYPH_COUNT; i++) {
    const text = glyphs[i % glyphs.length];   // cycle so every language is always present
    const color = COLORS[i % COLORS.length];
    const material = new THREE.SpriteMaterial({ map: textureFor(text, color), transparent: true, depthWrite: false });
    const sprite = new THREE.Sprite(material);
    const z = rand(-6, 3);
    sprite.position.set(rand(-13, 13), rand(-8, 8), z);
    const s = rand(0.35, 0.7);               // small, as asked: about 25–55 px on a laptop screen
    sprite.scale.set(s, s, 1);
    // WHY fade with depth: far syllables fainter, so they read as a soft background and never compete with the card.
    material.opacity = 0.18 + 0.32 * ((z + 6) / 9);
    sprite.userData = { speed: rand(0.12, 0.35), sway: rand(0.2, 0.6), phase: rand(0, Math.PI * 2), x0: sprite.position.x };
    group.add(sprite);
    sprites.push(sprite);
  }

  function resize() {
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener("resize", resize);

  // Gentle parallax: the cloud of letters leans a little towards the pointer.
  let targetX = 0, targetY = 0;
  const onPointer = (e) => {
    targetX = (e.clientX / window.innerWidth - 0.5) * 0.25;
    targetY = (e.clientY / window.innerHeight - 0.5) * 0.15;
  };
  window.addEventListener("pointermove", onPointer);

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clock = new THREE.Clock();
  let frame = null;

  function tick() {
    const dt = Math.min(clock.getDelta(), 0.05);   // WHY clamp: after a pause, letters shouldn't jump far
    const t = clock.elapsedTime;
    for (const sp of sprites) {
      const u = sp.userData;
      sp.position.y += u.speed * dt;                 // drift upward
      sp.position.x = u.x0 + Math.sin(t * 0.4 + u.phase) * u.sway;
      if (sp.position.y > 8.5) sp.position.y = -8.5; // wrap to the bottom
    }
    group.rotation.y += (targetX - group.rotation.y) * 0.03;
    group.rotation.x += (targetY - group.rotation.x) * 0.03;
    renderer.render(scene, camera);
    frame = requestAnimationFrame(tick);
  }

  // WHY: no animation loop while the tab is hidden (saves battery); and none at all under "reduce motion".
  const onVisibility = () => {
    if (document.hidden && frame) { cancelAnimationFrame(frame); frame = null; }
    else if (!document.hidden && !frame && !reduceMotion) { clock.getDelta(); frame = requestAnimationFrame(tick); }
  };
  document.addEventListener("visibilitychange", onVisibility);

  if (reduceMotion) renderer.render(scene, camera);   // one still picture
  else frame = requestAnimationFrame(tick);

  /** Stop and free everything (called once a language is chosen, so the chat stays fast). */
  return function stop() {
    if (frame) cancelAnimationFrame(frame);
    frame = null;
    window.removeEventListener("resize", resize);
    window.removeEventListener("pointermove", onPointer);
    document.removeEventListener("visibilitychange", onVisibility);
    sprites.forEach((s) => s.material.dispose());
    textures.forEach((t) => t.dispose());
    renderer.dispose();
  };
}
