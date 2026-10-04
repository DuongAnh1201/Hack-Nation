// One scene for the landing story. `progress` runs 0..CHAPTERS-1 with scroll;
// each chapter has a camera pose and decides which objects are visible.

import { Edges, Environment, Lightformer, Stars } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { SampleDesign } from "../lib/api";
import { materialInfo } from "../lib/materials";
import { layout, StackMesh, topOf, type Stack } from "./CoatingScene";
import { Photons, SkyLayer } from "./Photons";


// camera position, look-at target, per chapter
const POSES: [THREE.Vector3Tuple, THREE.Vector3Tuple][] = [
  // targets are shifted sideways so the object sits opposite the text card
  [[0, 2.2, 13], [-3.4, -0.3, 0]],          // 0 roof under the sun (headline bottom-left)
  [[-5.5, 3.6, 8.5], [1.7, 1.6, 1.1]],      // 1 sunlight bounces (card right)
  [[0, 5.5, 13], [-2.4, 3.4, 0]],           // 2 heat escapes through the sky window (card left)
  [[4.4, 2.4, 5.6], [1.0, 0.8, -0.8]],      // 3 inside the coating (card right)
  [[-1.5, 12.5, 12], [-3.6, 0, 0.6]],         // 4 the search space (card left)
  [[5, 3.4, 7.5], [1.7, 1.0, -1.1]],        // 5 the result (card right)
];
const smooth = (t: number) => t * t * (3 - 2 * t);

function CameraRig({ progress }: { progress: number }) {
  const { camera } = useThree();
  const look = useRef(new THREE.Vector3(0, 1, 0));
  const pos = useMemo(() => new THREE.Vector3(), []);
  const tgt = useMemo(() => new THREE.Vector3(), []);
  useFrame((_, dt) => {
    const i = Math.min(POSES.length - 2, Math.floor(progress));
    const k = smooth(Math.min(1, Math.max(0, progress - i)));
    pos.fromArray(POSES[i][0]).lerp(new THREE.Vector3(...POSES[i + 1][0]), k);
    tgt.fromArray(POSES[i][1]).lerp(new THREE.Vector3(...POSES[i + 1][1]), k);
    const a = 1 - Math.exp(-dt * 3);
    camera.position.lerp(pos, a);
    look.current.lerp(tgt, a);
    camera.lookAt(look.current);
  });
  return null;
}

/** Visibility 0..1 of something that lives between chapters a and b (inclusive), with soft edges. */
function vis(p: number, a: number, b: number) {
  return Math.max(0, Math.min(1, Math.min(p - a + 0.6, b - p + 0.6) / 0.6));
}

function Roof({ opacity }: { opacity: number }) {
  return (
    <group visible={opacity > 0.01}>
      <mesh position={[0, -0.25, 0]} receiveShadow>
        <boxGeometry args={[9, 0.3, 6]} />
        <meshStandardMaterial color="#26241f" roughness={0.95} transparent opacity={opacity} />
      </mesh>
      {Array.from({ length: 9 }, (_, i) => (
        <mesh key={i} position={[-4 + i, -0.09, 0]}>
          <boxGeometry args={[0.02, 0.01, 6]} />
          <meshBasicMaterial color="#3a372f" transparent opacity={opacity} />
        </mesh>
      ))}
    </group>
  );
}

function SunDisc({ opacity }: { opacity: number }) {
  return (
    <mesh position={[-9, 9.5, -6]} visible={opacity > 0.01}>
      <sphereGeometry args={[0.9, 32, 32]} />
      <meshBasicMaterial color="#ffd38a" toneMapped={false} transparent opacity={opacity} />
    </mesh>
  );
}

function SearchGrid({ designs, show, best }: { designs: SampleDesign[]; show: number; best?: number }) {
  const group = useRef<THREE.Group>(null!);
  const n = Math.ceil(Math.sqrt(designs.length));
  useFrame(() => { if (group.current) group.current.scale.setScalar(THREE.MathUtils.lerp(group.current.scale.x, show > 0.01 ? 1 : 0.001, 0.08)); });
  const maxP = Math.max(1, ...designs.map((d) => d.p_net_w_m2));
  return (
    <group ref={group} position={[0, -0.05, 0]} scale={0.001}>
      {designs.map((d, i) => {
        const gx = (i % n) - (n - 1) / 2, gz = Math.floor(i / n) - (n - 1) / 2;
        const cool = d.p_net_w_m2 > 0;
        const lit = best !== undefined && d.p_net_w_m2 >= best;
        let y = 0;
        return (
          <group key={i} position={[gx * 1.25, 0, gz * 1.25]}>
            {d.materials.map((m, k) => {
              const h = 0.05 + 0.18 * Math.sqrt(d.thicknesses_nm[k] / 800);
              const el = (
                <mesh key={k} position={[0, y + h / 2, 0]}>
                  <boxGeometry args={[0.8, h, 0.8]} />
                  <meshStandardMaterial color={materialInfo(m).color} transparent opacity={0.85}
                    emissive={cool ? "#5ad1ff" : "#ff5a36"} emissiveIntensity={cool ? 0.25 + 0.9 * (d.p_net_w_m2 / maxP) : 0.18} />
                </mesh>
              );
              y += h + 0.02;
              return el;
            })}
            <mesh position={[0, -0.03, 0]}>
              <boxGeometry args={[0.9, 0.04, 0.9]} />
              <meshStandardMaterial color={lit ? "#a8e6ff" : "#cfd6de"} metalness={1} roughness={0.25} emissive={lit ? "#a8e6ff" : "#000"} emissiveIntensity={lit ? 1.2 : 0} />
            </mesh>
            {!cool && <mesh position={[0, y + 0.12, 0]}><sphereGeometry args={[0.06, 12, 12]} /><meshBasicMaterial color="#ff5a36" toneMapped={false} /></mesh>}
          </group>
        );
      })}
    </group>
  );
}

function Exploded({ stack, spread }: { stack: Stack; spread: number }) {
  // the same stack, with the gaps opened up when we are "inside" the coating
  const ref = useRef<THREE.Group>(null!);
  useFrame(() => {
    if (!ref.current) return;
    ref.current.children.forEach((c, i) => { c.position.y = THREE.MathUtils.lerp(c.position.y, c.userData.base + i * 0.22 * spread, 0.08); });
  });
  const ls = layout(stack);
  return (
    <group ref={ref}>
      {ls.map((l, i) => (
        <mesh key={i} position={[0, l.y, 0]} userData={{ base: l.y }}>
          <boxGeometry args={[2.8, l.h, 2.0]} />
          <meshPhysicalMaterial color={materialInfo(l.m).color} transparent opacity={0.8} roughness={0.15} clearcoat={1} />
          <Edges color="#f4efe6" />
        </mesh>
      ))}
    </group>
  );
}

export function StoryScene({ progress, stack, reflectance, emissivity, designs, target }: {
  progress: number; stack: Stack; reflectance: number; emissivity: number; designs: SampleDesign[]; target: number;
}) {
  const top = topOf(stack);
  const pRoof = vis(progress, 0, 3), pSun = vis(progress, 0, 1.4), pHeat = vis(progress, 2, 3);
  const pInside = vis(progress, 3, 3), pGrid = vis(progress, 4, 4), pStack = progress < 3.5 || progress > 4.6 ? 1 : 0;
  return (
    <Canvas camera={{ position: POSES[0][0], fov: 40 }} dpr={[1, 2]} gl={{ antialias: true }}>
      <color attach="background" args={["#0b0a08"]} />
      <fog attach="fog" args={["#0b0a08", 16, 34]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[-9, 9.5, -6]} intensity={2.1} color="#ffd9a3" />
      <pointLight position={[4, 3, 5]} intensity={14} color="#8fd8f2" />
      <Environment resolution={256} frames={1}>
        <Lightformer intensity={2} position={[0, 5, -6]} scale={[12, 4, 1]} color="#ffffff" />
        <Lightformer intensity={1} position={[-6, 2, 2]} rotation={[0, Math.PI / 2, 0]} scale={[8, 3, 1]} color="#ffcf8a" />
      </Environment>
      <Stars radius={80} depth={40} count={2200} factor={3} saturation={0} fade speed={0.4} />
      <CameraRig progress={progress} />
      <SunDisc opacity={pSun} />
      <Roof opacity={pRoof} />
      <group visible={pStack > 0}>
        {pInside > 0.05 ? <Exploded stack={stack} spread={pInside} /> : <StackMesh stack={stack} x={0} ghost={false} mood="neutral" animate />}
      </group>
      <Photons top={top} reflectance={reflectance} emissivity={emissivity} sun={pSun > 0.3 && progress > 0.6} heat={pHeat > 0.3}
               skyY={4.2} animate />
      <group visible={pHeat > 0.05}><SkyLayer y={4.2} opacity={pHeat} /></group>
      <SearchGrid designs={designs} show={pGrid} best={target} />
      <EffectComposer>
        <Bloom mipmapBlur intensity={0.9} luminanceThreshold={0.55} luminanceSmoothing={0.2} />
        <Vignette eskil={false} offset={0.2} darkness={0.85} />
      </EffectComposer>
    </Canvas>
  );
}
