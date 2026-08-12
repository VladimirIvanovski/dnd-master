import { useEffect, useRef } from "react";
import * as THREE from "three";

type Props = {
  /** 1–20 predetermined natural roll */
  target: number;
  rolling: boolean;
  onSettled?: () => void;
  onBounce?: (intensity: number) => void;
  className?: string;
};

type FaceInfo = { normal: THREE.Vector3; centroid: THREE.Vector3 };
type Mode = "idle" | "toss" | "settle" | "show";

const DIE_R = 0.78;
const GRAVITY = -28;
const RESTITUTION = 0.48;
const FRICTION = 0.82;
const ANG_DAMP = 0.985;
const TABLE_HALF_W = 4.6;
const TABLE_HALF_D = 2.9;

function makeWoodTexture(): THREE.CanvasTexture {
  const size = 512;
  const c = document.createElement("canvas");
  c.width = size;
  c.height = size;
  const g = c.getContext("2d")!;
  g.fillStyle = "#3a2616";
  g.fillRect(0, 0, size, size);
  for (let i = 0; i < 70; i++) {
    const y = (i / 70) * size + Math.sin(i * 1.7) * 3;
    g.strokeStyle = `rgba(${40 + (i % 5) * 8},${24 + (i % 3) * 6},${12},0.35)`;
    g.lineWidth = 2 + (i % 3);
    g.beginPath();
    g.moveTo(0, y);
    for (let x = 0; x <= size; x += 16) {
      g.lineTo(x, y + Math.sin(x * 0.04 + i) * 4);
    }
    g.stroke();
  }
  // subtle scratches
  for (let i = 0; i < 40; i++) {
    g.strokeStyle = `rgba(255,220,170,${0.03 + Math.random() * 0.04})`;
    g.beginPath();
    const x = Math.random() * size;
    g.moveTo(x, 0);
    g.lineTo(x + (Math.random() - 0.5) * 30, size);
    g.stroke();
  }
  // felt strip in the center (gaming table vibe)
  const grd = g.createLinearGradient(0, size * 0.25, 0, size * 0.75);
  grd.addColorStop(0, "rgba(28,55,40,0)");
  grd.addColorStop(0.2, "rgba(28,55,40,0.85)");
  grd.addColorStop(0.8, "rgba(28,55,40,0.85)");
  grd.addColorStop(1, "rgba(28,55,40,0)");
  g.fillStyle = grd;
  g.fillRect(size * 0.08, size * 0.22, size * 0.84, size * 0.56);

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

function makeNumberSprite(n: number): THREE.Sprite {
  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const g = canvas.getContext("2d")!;
  g.clearRect(0, 0, size, size);
  // soft disc behind digit for readability from above
  g.beginPath();
  g.arc(size / 2, size / 2, 96, 0, Math.PI * 2);
  g.fillStyle = "rgba(12, 8, 20, 0.72)";
  g.fill();
  g.font = "bold 140px Cinzel, Georgia, serif";
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.lineWidth = 16;
  g.strokeStyle = "#05030a";
  g.strokeText(String(n), size / 2, size / 2 + 6);
  g.fillStyle = n === 20 ? "#ffe08a" : n === 1 ? "#ffb4b4" : "#ffffff";
  g.fillText(String(n), size / 2, size / 2 + 6);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthTest: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(0.72, 0.72, 0.72);
  return sprite;
}

function buildNumberedD20(): { mesh: THREE.Mesh; faces: FaceInfo[] } {
  const base = new THREE.IcosahedronGeometry(1, 0);
  const nonIndexed = base.toNonIndexed();
  base.dispose();
  const p = nonIndexed.attributes.position;
  const triCount = p.count / 3;
  const faces: FaceInfo[] = [];
  const faceColors: number[] = [];
  const body = new THREE.Color("#4c1d95");
  const deep = new THREE.Color("#1e1035");
  const gold = new THREE.Color("#c9a227");
  const crimson = new THREE.Color("#9f1239");
  const labels = new THREE.Group();

  for (let i = 0; i < triCount; i++) {
    const a = new THREE.Vector3().fromBufferAttribute(p, i * 3);
    const b = new THREE.Vector3().fromBufferAttribute(p, i * 3 + 1);
    const c = new THREE.Vector3().fromBufferAttribute(p, i * 3 + 2);
    const centroid = new THREE.Vector3().add(a).add(b).add(c).divideScalar(3);
    const normal = new THREE.Vector3()
      .subVectors(b, a)
      .cross(new THREE.Vector3().subVectors(c, a))
      .normalize();
    if (normal.dot(centroid) < 0) normal.negate();
    faces.push({ normal: normal.clone(), centroid: centroid.clone() });

    const n = i + 1;
    const tint = n === 20 ? gold : n === 1 ? crimson : body.clone().lerp(deep, (i % 5) * 0.06);
    for (let v = 0; v < 3; v++) faceColors.push(tint.r, tint.g, tint.b);

    const sprite = makeNumberSprite(n);
    sprite.position.copy(centroid.clone().multiplyScalar(1.12));
    labels.add(sprite);
  }

  nonIndexed.setAttribute("color", new THREE.Float32BufferAttribute(faceColors, 3));
  const material = new THREE.MeshPhysicalMaterial({
    vertexColors: true,
    metalness: 0.15,
    roughness: 0.28,
    clearcoat: 0.65,
    clearcoatRoughness: 0.25,
    flatShading: true,
  });
  const mesh = new THREE.Mesh(nonIndexed, material);
  mesh.castShadow = true;
  mesh.receiveShadow = false;
  mesh.scale.setScalar(DIE_R);
  mesh.add(labels);

  const edgeGeo = new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(1.01, 0));
  mesh.add(
    new THREE.LineSegments(
      edgeGeo,
      new THREE.LineBasicMaterial({ color: "#ddd6fe", transparent: true, opacity: 0.35 }),
    ),
  );

  return { mesh, faces };
}

/** Orient so chosen face normal points UP (+Y) toward the camera. */
function quatFaceUp(faceNormal: THREE.Vector3): THREE.Quaternion {
  const q = new THREE.Quaternion();
  q.setFromUnitVectors(faceNormal.clone().normalize(), new THREE.Vector3(0, 1, 0));
  return q;
}

function disposeObject(root: THREE.Object3D) {
  root.traverse((obj) => {
    if (obj instanceof THREE.Mesh) {
      obj.geometry.dispose();
      const m = obj.material;
      if (Array.isArray(m)) m.forEach((x) => x.dispose());
      else (m as THREE.Material).dispose();
    }
    if (obj instanceof THREE.Sprite) {
      obj.material.map?.dispose();
      obj.material.dispose();
    }
    if (obj instanceof THREE.LineSegments) {
      obj.geometry.dispose();
      (obj.material as THREE.Material).dispose();
    }
  });
}

export function Dice3D({ target, rolling, onSettled, onBounce, className }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const startTossRef = useRef<((n: number) => void) | null>(null);
  const onSettledRef = useRef(onSettled);
  const onBounceRef = useRef(onBounce);
  onSettledRef.current = onSettled;
  onBounceRef.current = onBounce;
  const rollingLock = useRef(false);

  useEffect(() => {
    const el = mountRef.current;
    if (!el) return;

    const w = el.clientWidth || 640;
    const h = el.clientHeight || 360;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0a0810, 0.045);

    const camera = new THREE.PerspectiveCamera(34, w / h, 0.1, 100);
    // High angle so the upward face reads clearly
    camera.position.set(0, 7.8, 4.2);
    camera.lookAt(0, 0.2, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, h);
    renderer.setClearColor(0x000000, 0);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(renderer.domElement);

    const hemi = new THREE.HemisphereLight(0xfff1d6, 0x1a1520, 0.55);
    scene.add(hemi);
    const key = new THREE.DirectionalLight(0xffe6c8, 1.35);
    key.position.set(3.5, 8, 4);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.near = 1;
    key.shadow.camera.far = 24;
    key.shadow.camera.left = -6;
    key.shadow.camera.right = 6;
    key.shadow.camera.top = 6;
    key.shadow.camera.bottom = -6;
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xa78bfa, 0.35);
    fill.position.set(-4, 3, -2);
    scene.add(fill);
    const candle = new THREE.PointLight(0xffb070, 0.55, 14);
    candle.position.set(-2.5, 1.2, 1.5);
    scene.add(candle);

    // Table top
    const wood = makeWoodTexture();
    const table = new THREE.Mesh(
      new THREE.BoxGeometry(TABLE_HALF_W * 2.15, 0.18, TABLE_HALF_D * 2.15),
      new THREE.MeshStandardMaterial({
        map: wood,
        roughness: 0.75,
        metalness: 0.05,
      }),
    );
    table.position.y = -0.09;
    table.receiveShadow = true;
    scene.add(table);

    // Table edge / lip
    const lip = new THREE.Mesh(
      new THREE.BoxGeometry(TABLE_HALF_W * 2.2, 0.12, TABLE_HALF_D * 2.2),
      new THREE.MeshStandardMaterial({ color: "#2a1a10", roughness: 0.9 }),
    );
    lip.position.y = -0.22;
    lip.receiveShadow = true;
    scene.add(lip);

    // Soft contact shadow disc
    const shadowMat = new THREE.MeshBasicMaterial({
      color: 0x000000,
      transparent: true,
      opacity: 0.35,
      depthWrite: false,
    });
    const contactShadow = new THREE.Mesh(new THREE.CircleGeometry(0.95, 32), shadowMat);
    contactShadow.rotation.x = -Math.PI / 2;
    contactShadow.position.y = 0.01;
    scene.add(contactShadow);

    const { mesh, faces } = buildNumberedD20();
    scene.add(mesh);

    // Large readable result label hovering above the settled face
    let resultSprite = makeNumberSprite(20);
    resultSprite.scale.set(1.6, 1.6, 1.6);
    resultSprite.visible = false;
    resultSprite.material.depthTest = false;
    resultSprite.renderOrder = 10;
    scene.add(resultSprite);

    const showResultLabel = (n: number) => {
      const fresh = makeNumberSprite(n);
      resultSprite.material.map?.dispose();
      (resultSprite.material as THREE.SpriteMaterial).dispose();
      scene.remove(resultSprite);
      resultSprite = fresh;
      resultSprite.scale.set(1.7, 1.7, 1.7);
      resultSprite.visible = true;
      resultSprite.material.depthTest = false;
      resultSprite.renderOrder = 10;
      scene.add(resultSprite);
    };

    // Idle pose: resting on table, slight presentational spin
    mesh.position.set(-1.6, DIE_R, 0.4);
    mesh.quaternion.copy(quatFaceUp(faces[19].normal)); // show 20 while waiting

    let mode: Mode = "idle";
    let raf = 0;
    let last = performance.now();
    let targetFace = 20;
    let settled = false;
    let settleStart = 0;
    const vel = new THREE.Vector3();
    const angVel = new THREE.Vector3();
    const startQuat = new THREE.Quaternion();
    const endQuat = new THREE.Quaternion();
    let bounceCool = 0;
    let idleAngle = 0;

    const clampToTable = (p: THREE.Vector3) => {
      p.x = Math.max(-TABLE_HALF_W + DIE_R, Math.min(TABLE_HALF_W - DIE_R, p.x));
      p.z = Math.max(-TABLE_HALF_D + DIE_R, Math.min(TABLE_HALF_D - DIE_R, p.z));
    };

    const startToss = (n: number) => {
      settled = false;
      targetFace = Math.max(1, Math.min(20, Math.round(n)));
      // Throw from near-camera / "hand" side across the table
      mesh.position.set(-3.2, 1.8 + Math.random() * 0.4, 1.2 + Math.random() * 0.4);
      vel.set(
        5.5 + Math.random() * 2.2,
        2.2 + Math.random() * 1.5,
        -2.8 - Math.random() * 1.6,
      );
      angVel.set(
        (Math.random() - 0.5) * 28,
        (Math.random() - 0.5) * 32,
        (Math.random() - 0.5) * 28,
      );
      mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
      bounceCool = 0;
      resultSprite.visible = false;
      mode = "toss";
    };
    startTossRef.current = startToss;

    const animate = (now: number) => {
      raf = requestAnimationFrame(animate);
      const dt = Math.min(0.033, (now - last) / 1000);
      last = now;
      bounceCool = Math.max(0, bounceCool - dt);

      // candle flicker
      candle.intensity = 0.45 + Math.sin(now * 0.008) * 0.08 + Math.random() * 0.03;

      if (mode === "idle") {
        idleAngle += dt * 0.35;
        mesh.position.set(-1.4, DIE_R, 0.35);
        mesh.rotation.set(0.15, idleAngle, 0.08);
        contactShadow.position.set(mesh.position.x, 0.012, mesh.position.z);
        contactShadow.scale.setScalar(1);
        shadowMat.opacity = 0.28;
      } else if (mode === "toss") {
        vel.y += GRAVITY * dt;
        mesh.position.addScaledVector(vel, dt);

        // integrate spin
        const spin = new THREE.Quaternion().setFromEuler(
          new THREE.Euler(angVel.x * dt, angVel.y * dt, angVel.z * dt),
        );
        mesh.quaternion.multiply(spin);
        angVel.multiplyScalar(ANG_DAMP);

        // table collision
        if (mesh.position.y <= DIE_R) {
          mesh.position.y = DIE_R;
          const impact = Math.abs(vel.y);
          if (impact > 0.8 && bounceCool <= 0) {
            onBounceRef.current?.(Math.min(1, impact / 12));
            bounceCool = 0.08;
          }
          if (impact > 0.6) {
            vel.y = -vel.y * RESTITUTION;
            vel.x *= FRICTION;
            vel.z *= FRICTION;
            angVel.x += (Math.random() - 0.5) * impact * 0.8;
            angVel.z += (Math.random() - 0.5) * impact * 0.8;
            angVel.multiplyScalar(0.88);
          } else {
            vel.y = 0;
            vel.x *= 0.9;
            vel.z *= 0.9;
            angVel.multiplyScalar(0.9);
          }
        }

        // soft walls
        if (Math.abs(mesh.position.x) > TABLE_HALF_W - DIE_R) {
          mesh.position.x = Math.sign(mesh.position.x) * (TABLE_HALF_W - DIE_R);
          vel.x *= -0.55;
          if (bounceCool <= 0) {
            onBounceRef.current?.(0.35);
            bounceCool = 0.1;
          }
        }
        if (Math.abs(mesh.position.z) > TABLE_HALF_D - DIE_R) {
          mesh.position.z = Math.sign(mesh.position.z) * (TABLE_HALF_D - DIE_R);
          vel.z *= -0.55;
          if (bounceCool <= 0) {
            onBounceRef.current?.(0.3);
            bounceCool = 0.1;
          }
        }
        clampToTable(mesh.position);

        contactShadow.position.set(mesh.position.x, 0.012, mesh.position.z);
        const air = Math.max(0, mesh.position.y - DIE_R);
        contactShadow.scale.setScalar(1 + air * 0.35);
        shadowMat.opacity = Math.max(0.08, 0.4 - air * 0.12);

        const speed = vel.length() + angVel.length() * 0.15;
        const grounded = mesh.position.y <= DIE_R + 0.002;
        if (grounded && speed < 1.15) {
          mode = "settle";
          settleStart = now;
          startQuat.copy(mesh.quaternion);
          endQuat.copy(quatFaceUp(faces[targetFace - 1].normal));
          vel.set(0, 0, 0);
          angVel.set(0, 0, 0);
          mesh.position.y = DIE_R;
        }
      } else if (mode === "settle") {
        const u = Math.min(1, (now - settleStart) / 450);
        const e = 1 - (1 - u) ** 2.5;
        mesh.quaternion.slerpQuaternions(startQuat, endQuat, e);
        mesh.position.y = DIE_R;
        contactShadow.position.set(mesh.position.x, 0.012, mesh.position.z);
        contactShadow.scale.setScalar(1);
        shadowMat.opacity = 0.4;
        // Pull camera overhead onto the resting die for a clear top read
        const camTarget = new THREE.Vector3(
          mesh.position.x * 0.35,
          6.4,
          mesh.position.z * 0.35 + 2.4,
        );
        camera.position.lerp(camTarget, 0.08);
        camera.lookAt(mesh.position.x, DIE_R, mesh.position.z);
        if (u >= 1 && !settled) {
          settled = true;
          mesh.quaternion.copy(endQuat);
          mode = "show";
          showResultLabel(targetFace);
          onSettledRef.current?.();
        }
      } else if (mode === "show") {
        mesh.position.y = DIE_R;
        contactShadow.position.set(mesh.position.x, 0.012, mesh.position.z);
        resultSprite.position.set(
          mesh.position.x,
          DIE_R + 1.35,
          mesh.position.z,
        );
        const camTarget = new THREE.Vector3(
          mesh.position.x * 0.25,
          6.6,
          mesh.position.z * 0.25 + 2.2,
        );
        camera.position.lerp(camTarget, 0.06);
        camera.lookAt(mesh.position.x, DIE_R + 0.2, mesh.position.z);
      }

      renderer.render(scene, camera);
    };
    raf = requestAnimationFrame(animate);

    const onResize = () => {
      if (!mountRef.current) return;
      const nw = mountRef.current.clientWidth;
      const nh = mountRef.current.clientHeight;
      camera.aspect = nw / Math.max(nh, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      startTossRef.current = null;
      disposeObject(mesh);
      disposeObject(table);
      disposeObject(lip);
      disposeObject(contactShadow);
      resultSprite.material.map?.dispose();
      (resultSprite.material as THREE.SpriteMaterial).dispose();
      wood.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === el) el.removeChild(renderer.domElement);
    };
  }, []);

  useEffect(() => {
    if (!rolling || rollingLock.current) return;
    rollingLock.current = true;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      onSettledRef.current?.();
      return;
    }
    startTossRef.current?.(target);
  }, [rolling, target]);

  return <div ref={mountRef} className={className} aria-hidden />;
}
