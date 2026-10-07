// Esfera.jsx — Fondo 3D: una esfera de puntos conectados que gira y sigue al mouse.
// three.js se descarga aparte (import dinamico) para no pesar en la carga inicial.
// Si WebGL no esta disponible o el usuario pidio menos movimiento, no se dibuja nada.
import { useEffect, useRef } from "react";
import { useAmbiente } from "./ambiente";

export default function Esfera() {
  const canvasRef = useRef(null);
  const escena = useRef(null);
  const { color, entrado, fx } = useAmbiente();
  const objetivo = useRef(entrado ? 1 : 0);
  useEffect(() => { objetivo.current = entrado ? 1 : 0; }, [entrado]);

  useEffect(() => {
    if (!fx || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;
    let vivo = true, raf = 0, limpiar = () => {};
    import("three").then((THREE) => {
      const canvas = canvasRef.current;
      if (!vivo || !canvas) return;
      let renderer;
      try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true }); } catch { return; }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100);
      camera.position.z = 3.4;
      const grupo = new THREE.Group();
      scene.add(grupo);

      // Puntos repartidos en la esfera (espiral de Fibonacci)
      const N = 340, R = 1.5;
      const pos = new Float32Array(N * 3), pts = [];
      for (let i = 0; i < N; i++) {
        const y = 1 - (i / (N - 1)) * 2;
        const r = Math.sqrt(Math.max(0, 1 - y * y));
        const phi = i * 2.399963;
        const v = new THREE.Vector3(Math.cos(phi) * r * R, y * R, Math.sin(phi) * r * R);
        pts.push(v); pos[i * 3] = v.x; pos[i * 3 + 1] = v.y; pos[i * 3 + 2] = v.z;
      }
      const col = new THREE.Color(color);
      const pg = new THREE.BufferGeometry();
      pg.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      // Puntos redondos con borde suave: de cerca (al sumergirse) no se ven como cuadrados.
      const lienzo = document.createElement("canvas");
      lienzo.width = lienzo.height = 64;
      const c2d = lienzo.getContext("2d");
      const grad = c2d.createRadialGradient(32, 32, 0, 32, 32, 32);
      grad.addColorStop(0, "rgba(255,255,255,1)");
      grad.addColorStop(0.45, "rgba(255,255,255,0.9)");
      grad.addColorStop(1, "rgba(255,255,255,0)");
      c2d.fillStyle = grad;
      c2d.fillRect(0, 0, 64, 64);
      const punto = new THREE.CanvasTexture(lienzo);
      const pmat = new THREE.PointsMaterial({ color: col, size: 0.05, map: punto, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false });
      grupo.add(new THREE.Points(pg, pmat));

      // Lineas entre puntos cercanos
      const lpos = []; let seg = 0;
      for (let i = 0; i < N && seg < 540; i++)
        for (let j = i + 1; j < N && seg < 540; j++)
          if (pts[i].distanceTo(pts[j]) < 0.42) { lpos.push(pts[i].x, pts[i].y, pts[i].z, pts[j].x, pts[j].y, pts[j].z); seg++; }
      const lg = new THREE.BufferGeometry();
      lg.setAttribute("position", new THREE.Float32BufferAttribute(lpos, 3));
      const lmat = new THREE.LineBasicMaterial({ color: col.clone(), transparent: true, opacity: 0.13, blending: THREE.AdditiveBlending, depthWrite: false });
      grupo.add(new THREE.LineSegments(lg, lmat));

      const resize = () => {
        const w = canvas.clientWidth || window.innerWidth, h = canvas.clientHeight || window.innerHeight;
        renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
      };
      resize();
      window.addEventListener("resize", resize);
      let mx = 0, my = 0;
      const mouse = (e) => { mx = e.clientX / window.innerWidth - 0.5; my = e.clientY / window.innerHeight - 0.5; };
      window.addEventListener("mousemove", mouse, { passive: true });

      let b = objetivo.current;
      const t0 = performance.now();
      const animar = () => {
        const t = (performance.now() - t0) / 1000;
        b += (objetivo.current - b) * 0.018;
        grupo.rotation.y = t * (0.08 - b * 0.055);
        grupo.rotation.x = Math.sin(t * 0.15) * (0.16 + b * 0.1);
        grupo.scale.setScalar(1 + b * 1.25);
        camera.position.x += (mx * 1.3 - camera.position.x) * 0.04;
        camera.position.y += (-my * 1.0 - camera.position.y) * 0.04;
        camera.position.z += ((3.4 - b * 2.25) - camera.position.z) * 0.04;
        pmat.opacity = 0.9 - b * 0.52;
        lmat.opacity = 0.13 - b * 0.06;
        camera.lookAt(0, 0, 0);
        renderer.render(scene, camera);
        raf = requestAnimationFrame(animar);
      };
      animar();
      escena.current = { pmat, lmat, THREE };
      limpiar = () => {
        cancelAnimationFrame(raf);
        window.removeEventListener("resize", resize);
        window.removeEventListener("mousemove", mouse);
        pg.dispose(); lg.dispose(); punto.dispose(); pmat.dispose(); lmat.dispose(); renderer.dispose();
        escena.current = null;
      };
    }).catch(() => { /* sin three: fondo plano */ });
    return () => { vivo = false; limpiar(); };
    // el color se actualiza en el efecto de abajo sin recrear la escena
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fx]);

  useEffect(() => {
    const e = escena.current;
    if (!e) return;
    const c = new e.THREE.Color(color);
    e.pmat.color.set(c);
    e.lmat.color.set(c);
  }, [color]);

  if (!fx) return null;
  // Como en el prototipo: el globo se atenua un poco al sumergirse (la transicion la hace el CSS).
  return <canvas ref={canvasRef} className="ll-esfera" style={{ opacity: entrado ? 0.7 : 0.92 }} aria-hidden="true" />;
}
