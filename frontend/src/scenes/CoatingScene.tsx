// 3D view of the coating: an exploded stack of thin films on a silver mirror.
// Sunlight (amber) bounces off; heat (coral) escapes upward to space.
// Layer heights are sqrt-scaled so thin films stay visible; the legend gives true nm.

import { Edges, Environment, Lightformer, Line, OrbitControls, Stars } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import { Component, type ReactNode, useMemo, useRef } from "react";
import * as THREE from "three";
import { materialInfo } from "../lib/materials";

export interface Stack { materials: string[]; thicknessesNm: number[]; substrate: string }
type Mood = "neutral" | "refuted" | "supported";

const W = 2.8, D = 2.0, MIRROR = 0.16, GAP = 0.06;
const layerH = (nm: number) => 0.1 + 0.5 * Math.sqrt(Math.max(nm, 1) / 800);

function layout(s: Stack) {
  let y = MIRROR + GAP;
  return s.materials.map((m, i) => {
    const h = layerH(s.thicknessesNm[i] ?? 100);
    const out = { m, h, y: y + h / 2 };
    y += h + GAP;
    return out;
  });
}
const topOf = (s: Stack) => layout(s).reduce((t, l) => Math.max(t, l.y + l.h / 2), MIRROR);

const MOOD = { neutral: new THREE.Color("#000000"), refuted: new THREE.Color("#ff2d4a"), supported: new THREE.Color("#19d38a") };
const tmp = new THREE.Color();

function Layer({ y, h, color, ghost, mood, animate }: { y: number; h: number; color: string; ghost: boolean; mood: Mood; animate: boolean }) {
  const mesh = useRef<THREE.Mesh>(null!);
  const mat = useRef<THREE.MeshPhysicalMaterial>(null!);
  useFrame((_, dt) => {
    const k = animate ? 1 - Math.exp(-dt * 5) : 1;
    mesh.current.position.y += (y - mesh.current.position.y) * k;
    mesh.current.scale.y += (h - mesh.current.scale.y) * k;
    mat.current.color.lerp(tmp.set(color), k);
    mat.current.emissive.lerp(ghost ? MOOD.neutral : MOOD[mood], k * 0.6);
  });
  return (
    <mesh ref={mesh} position={[0, animate ? y + 1.6 : y, 0]} scale={[1, animate ? 0.001 : h, 1]}>
      <boxGeometry args={[W, 1, D]} />
      <meshPhysicalMaterial ref={mat} color={color} transparent opacity={ghost ? 0.22 : 0.8} roughness={0.15}
                            clearcoat={1} clearcoatRoughness={0.15} emissiveIntensity={0.5} depthWrite={!ghost} />
      <Edges color={ghost ? "#6f7c97" : "#e8f6ff"} />
    </mesh>
  );
}

function StackMesh({ stack, x, ghost, mood, animate }: { stack: Stack; x: number; ghost: boolean; mood: Mood; animate: boolean }) {
  const layers = layout(stack);
  return (
    <group position={[x, 0, 0]}>
      <mesh position={[0, MIRROR / 2, 0]}>
        <boxGeometry args={[W + 0.3, MIRROR, D + 0.3]} />
        <meshStandardMaterial color="#dfe7f0" metalness={1} roughness={0.18} transparent={ghost} opacity={ghost ? 0.35 : 1} />
      </mesh>
      {layers.map((l, i) => (
        <Layer key={i} y={l.y} h={l.h} color={materialInfo(l.m).color} ghost={ghost} mood={mood} animate={animate} />
      ))}
    </group>
  );
}

function SunRays({ x, top, animate }: { x: number; top: number; animate: boolean }) {
  const refs = useRef<Array<{ material: { dashOffset: number } } | null>>([]);
  useFrame((_, dt) => { if (animate) refs.current.forEach((l) => { if (l) l.material.dashOffset -= dt * 0.9; }); });
  const rays = useMemo(() => [-0.6, 0, 0.6].map((dz) => [
    new THREE.Vector3(x - 4.2, top + 4.2, dz - 0.6), new THREE.Vector3(x - 0.2, top + 0.02, dz), new THREE.Vector3(x + 3.8, top + 4.0, dz + 0.6),
  ]), [x, top]);
  return (
    <group>
      {rays.map((pts, i) => (
        <Line key={i} ref={(l) => { refs.current[i] = l as unknown as { material: { dashOffset: number } } | null; }}
              points={pts} color="#ffb547" lineWidth={2.2} dashed dashSize={0.32} gapSize={0.2} toneMapped={false} transparent opacity={0.95} />
      ))}
    </group>
  );
}

function HeatWaves({ x, top, animate }: { x: number; top: number; animate: boolean }) {
  const group = useRef<THREE.Group>(null!);
  const lines = useRef<Array<{ material: { opacity: number } } | null>>([]);
  const waves = useMemo(() => [-0.8, 0, 0.8].map((dx, k) => Array.from({ length: 48 }, (_, i) => {
    const t = i / 47;
    return new THREE.Vector3(x + dx + 0.12 * Math.sin(t * 18 + k), top + 0.2 + t * 2.6, 0.25 * Math.cos(t * 9 + k));
  })), [x, top]);
  useFrame(({ clock }) => {
    const f = animate ? (clock.elapsedTime * 0.35) % 1 : 0.3;
    group.current.position.y = f * 1.4;
    lines.current.forEach((l) => { if (l) l.material.opacity = 0.9 * (1 - f); });
  });
  return (
    <group>
      <group ref={group}>
        {waves.map((pts, i) => (
          <Line key={i} ref={(l) => { lines.current[i] = l as unknown as { material: { opacity: number } } | null; }}
                points={pts} color="#ff6b5b" lineWidth={2} toneMapped={false} transparent opacity={0.9} />
        ))}
      </group>
    </group>
  );
}

export function CoatingScene({ stack, reference, compare, mood, animate }: {
  stack?: Stack; reference?: Stack; compare: boolean; mood: Mood; animate: boolean;
}) {
  const showRef = compare && reference;
  const x = showRef ? 1.9 : 0;
  const top = stack ? topOf(stack) : MIRROR;
  return (
    <SceneBoundary>
      <Canvas camera={{ position: [5.8, 3.9, 7.4], fov: 38 }} dpr={[1, 2]} gl={{ antialias: true }}>
        <color attach="background" args={["#04060c"]} />
        <fog attach="fog" args={["#04060c", 14, 30]} />
        <ambientLight intensity={0.35} />
        <directionalLight position={[-5, 9, 4]} intensity={1.6} color="#ffd9a3" />
        <pointLight position={[4, 3, 4]} intensity={18} color="#5ad1ff" />
        <Environment resolution={256} frames={1}>
          <Lightformer intensity={2.2} position={[0, 5, -6]} scale={[12, 4, 1]} color="#ffffff" />
          <Lightformer intensity={1.2} position={[-6, 2, 2]} rotation={[0, Math.PI / 2, 0]} scale={[8, 3, 1]} color="#9be7ff" />
          <Lightformer intensity={0.8} position={[6, 1, 2]} rotation={[0, -Math.PI / 2, 0]} scale={[8, 3, 1]} color="#ffb547" />
        </Environment>
        <Stars radius={70} depth={40} count={1800} factor={3.2} saturation={0} fade speed={animate ? 0.6 : 0} />
        {showRef && <StackMesh stack={reference} x={-1.9} ghost mood="neutral" animate={animate} />}
        {stack && (
          <>
            <StackMesh stack={stack} x={x} ghost={false} mood={mood} animate={animate} />
            <SunRays x={x} top={top} animate={animate} />
            <HeatWaves x={x} top={top} animate={animate} />
          </>
        )}
        <OrbitControls target={[0, 1.1, 0]} enablePan={false} minDistance={6} maxDistance={16}
                       minPolarAngle={0.35} maxPolarAngle={1.45} autoRotate={animate && !showRef} autoRotateSpeed={0.35} />
        <EffectComposer>
          <Bloom mipmapBlur intensity={0.85} luminanceThreshold={0.5} luminanceSmoothing={0.2} />
        </EffectComposer>
      </Canvas>
    </SceneBoundary>
  );
}

class SceneBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) {
      return <div style={{ display: "grid", placeItems: "center", height: "100%", color: "#a4b1cc" }}>3D view needs WebGL; the rest of the lab still works.</div>;
    }
    return this.props.children;
  }
}
