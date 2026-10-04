// Photon flow driven by real simulation results:
// - sunlight photons hit the coating; a fraction `reflectance` bounces off, the rest is absorbed (flashes and fades);
// - heat photons leave the surface at a rate set by the 8-13 um emissivity; at the sky layer a
//   fraction `skyTransmission` escapes to space, the rest is sent back by the atmosphere.
// Nothing is exaggerated: the shares on screen are the simulated shares.

import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

const SUN = new THREE.Color("#f2ad45");
const ABSORBED = new THREE.Color("#ff5a36");
const HEAT = new THREE.Color("#ff6a4d");
const SPACE = new THREE.Color("#a8e6ff");
const HIDDEN = new THREE.Vector3(0, -999, 0);

export interface PhotonProps {
  x?: number;            // stack centre
  top: number;           // height of the coating surface
  width?: number;        // footprint of the coating
  reflectance: number;   // simulated solar reflectance (0-1)
  emissivity: number;    // simulated mean emissivity in 8-13 um (0-1)
  skyTransmission?: number; // share of window radiation the sky lets through
  skyY?: number;         // height of the atmosphere layer
  sun?: boolean;
  heat?: boolean;
  animate?: boolean;
  count?: number;
}

export function Photons({ x = 0, top, width = 2.6, reflectance, emissivity, skyTransmission = 0.76, skyY = 4.2,
  sun = true, heat = true, animate = true, count = 180 }: PhotonProps) {
  const sunMesh = useRef<THREE.InstancedMesh>(null!);
  const heatMesh = useRef<THREE.InstancedMesh>(null!);
  const sunP = useMemo(() => Array.from({ length: count }, () => ({ t: Math.random(), u: Math.random() - 0.5, v: Math.random() - 0.5, fate: Math.random() })), [count]);
  const heatP = useMemo(() => Array.from({ length: Math.round(count * 0.8) }, () => ({
    t: Math.random(), u: Math.random() - 0.5, v: Math.random() - 0.5, emit: Math.random(), pass: Math.random(), w: Math.random() * 6.28 })), [count]);
  const tmp = useMemo(() => ({ m: new THREE.Matrix4(), q: new THREE.Quaternion(), s: new THREE.Vector3(), p: new THREE.Vector3(), a: new THREE.Vector3(), b: new THREE.Vector3(), c: new THREE.Color() }), []);

  useFrame((_, dtRaw) => {
    const dt = animate ? Math.min(dtRaw, 0.05) : 0;
    const { m, q, s, p, a, b, c } = tmp;
    if (sun && sunMesh.current) {
      sunP.forEach((o, i) => {
        o.t += dt * 0.32;
        if (o.t > 1) { o.t -= 1; o.fate = Math.random(); o.u = Math.random() - 0.5; o.v = Math.random() - 0.5; }
        b.set(x + o.u * width * 0.9, top, o.v * width * 0.7);
        a.set(b.x - 4.2, b.y + 6, b.z - 0.8);
        let size = 0.04;
        if (o.t < 0.5) { p.lerpVectors(a, b, o.t / 0.5); c.copy(SUN); }
        else if (o.fate < reflectance) { const k = (o.t - 0.5) / 0.5; p.set(b.x + 4.2 * k, b.y + 6 * k, b.z + 0.8 * k); c.copy(SUN); }
        else { const k = (o.t - 0.5) / 0.5; p.copy(b); c.copy(ABSORBED); size = 0.09 * (1 - k); }
        m.compose(p, q, s.setScalar(size));
        sunMesh.current.setMatrixAt(i, m);
        sunMesh.current.setColorAt(i, c);
      });
      sunMesh.current.instanceMatrix.needsUpdate = true;
      if (sunMesh.current.instanceColor) sunMesh.current.instanceColor.needsUpdate = true;
    }
    if (heat && heatMesh.current) {
      heatP.forEach((o, i) => {
        o.t += dt * 0.22;
        if (o.t > 1) { o.t -= 1; o.emit = Math.random(); o.pass = Math.random(); o.u = Math.random() - 0.5; o.v = Math.random() - 0.5; }
        if (o.emit > emissivity) { m.compose(HIDDEN, q, s.setScalar(0)); heatMesh.current.setMatrixAt(i, m); return; }
        const y0 = top, rise = skyY - top;
        const bx = x + o.u * width * 0.9 + Math.sin(o.t * 14 + o.w) * 0.05, bz = o.v * width * 0.7;
        let y: number, size = 0.035;
        if (o.t < 0.55) { y = y0 + rise * (o.t / 0.55); c.copy(HEAT); }
        else if (o.pass < skyTransmission) { const k = (o.t - 0.55) / 0.45; y = skyY + k * 4.5; c.copy(HEAT).lerp(SPACE, Math.min(1, k * 1.6)); size = 0.035 * (1 - k * 0.5); }
        else { const k = (o.t - 0.55) / 0.45; y = skyY - k * 1.2; c.copy(HEAT); size = 0.035 * (1 - k); }
        p.set(bx, y, bz);
        m.compose(p, q, s.setScalar(size));
        heatMesh.current.setMatrixAt(i, m);
        heatMesh.current.setColorAt(i, c);
      });
      heatMesh.current.instanceMatrix.needsUpdate = true;
      if (heatMesh.current.instanceColor) heatMesh.current.instanceColor.needsUpdate = true;
    }
  });

  return (
    <group>
      {sun && (
        <instancedMesh ref={sunMesh} args={[undefined, undefined, sunP.length]} frustumCulled={false}>
          <sphereGeometry args={[1, 8, 8]} />
          <meshBasicMaterial toneMapped={false} />
        </instancedMesh>
      )}
      {heat && (
        <instancedMesh ref={heatMesh} args={[undefined, undefined, heatP.length]} frustumCulled={false}>
          <sphereGeometry args={[1, 8, 8]} />
          <meshBasicMaterial toneMapped={false} />
        </instancedMesh>
      )}
    </group>
  );
}

/** A faint layer of atmosphere with the 8-13 um window shown as a brighter band. */
export function SkyLayer({ y = 4.2, size = 14, opacity = 1 }: { y?: number; size?: number; opacity?: number }) {
  return (
    <group position={[0, y, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[size, size]} />
        <meshBasicMaterial color="#5f86a8" transparent opacity={0.07 * opacity} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[1.2, 1.26, 96]} />
        <meshBasicMaterial color="#a8e6ff" transparent opacity={0.35 * opacity} depthWrite={false} toneMapped={false} />
      </mesh>
    </group>
  );
}
