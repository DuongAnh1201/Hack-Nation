// Landing page: one fixed 3D scene, six chapters that drive it with scroll.
// Every number on this page is fetched from the simulator API; nothing is typed in by hand.

import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, type SampleDesign, type SimResult } from "../lib/api";
import { encodeDesign, PRESETS } from "../lib/designs";
import { formula, materialInfo } from "../lib/materials";

const StoryScene = lazy(() => import("../scenes/StoryScene").then((m) => ({ default: m.StoryScene })));
const FEATURED = PRESETS[0].design;
const CHAPTERS = ["Noon", "Mirror", "Window", "Inside", "Search", "Yours"];

function useScrollChapters(n: number) {
  const refs = useRef<(HTMLElement | null)[]>([]);
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const y = window.scrollY + window.innerHeight * 0.35;
        const tops = refs.current.map((el) => (el ? el.offsetTop : 0));
        let p = 0;
        for (let i = 0; i < n; i++) {
          const a = tops[i], b = i + 1 < n ? tops[i + 1] : a + window.innerHeight;
          if (y >= a) p = i + Math.min(1, (y - a) / Math.max(1, b - a));
        }
        setProgress(Math.round(Math.min(n - 1, p) * 100) / 100);
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); };
  }, [n]);
  return { refs, progress };
}

const pct = (v?: number) => (v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);
const w = (v?: number, d = 1) => (v === undefined ? "—" : v.toFixed(d));

export function StoryPage() {
  const { refs, progress } = useScrollChapters(CHAPTERS.length);
  const [sim, setSim] = useState<SimResult>();
  const [designs, setDesigns] = useState<SampleDesign[]>([]);
  const [target, setTarget] = useState<number>();
  const [control, setControl] = useState<{ sim?: number; pub?: number }>({});
  const [error, setError] = useState<string>();

  useEffect(() => {
    api.simulate(FEATURED).then(setSim).catch((e: Error) => setError(e.message));
    api.sample(36, 7).then((r) => setDesigns(r.designs)).catch(() => {});
    api.benchmark().then((b) => setTarget(b.target_w_m2)).catch(() => {});
    api.control().then((c) => {
      const s = c as { simulated?: { p_net_w_m2?: number }; published?: { cooling_power_w_m2?: number } };
      setControl({ sim: s.simulated?.p_net_w_m2, pub: s.published?.cooling_power_w_m2 });
    }).catch(() => {});
  }, []);

  const stats = useMemo(() => {
    if (!designs.length) return undefined;
    const p = designs.map((d) => d.p_net_w_m2);
    return { n: p.length, cool: p.filter((v) => v > 0).length, hit: target === undefined ? 0 : p.filter((v) => v >= target).length,
             min: Math.min(...p), max: Math.max(...p) };
  }, [designs, target]);

  const stack = { materials: FEATURED.materials, thicknessesNm: FEATURED.thicknesses_nm, substrate: FEATURED.substrate };
  const active = Math.min(CHAPTERS.length - 1, Math.round(progress));
  const set = (i: number) => (el: HTMLElement | null) => { refs.current[i] = el; };
  const jump = (i: number) => refs.current[i]?.scrollIntoView({ behavior: "smooth" });

  return (
    <div className="story-root">
      <div className="story-canvas" aria-hidden>
        <Suspense fallback={null}>
          <StoryScene progress={progress} stack={stack} designs={designs} target={target ?? 50}
                      reflectance={sim?.solar_reflectance ?? 0.95} emissivity={sim?.window_emissivity ?? 0.8} />
        </Suspense>
      </div>

      <nav className="story-rail" aria-label="Chapters">
        {CHAPTERS.map((c, i) => (
          <button key={c} className={i === active ? "on" : undefined} onClick={() => jump(i)} aria-current={i === active}>
            <span className="n">{String(i + 1).padStart(2, "0")}</span><span className="t">{c}</span>
          </button>
        ))}
      </nav>

      {error && <div className="story-error">Simulator API is not reachable ({error}). Start the backend on :8000.</div>}

      <section ref={set(0)} className="chapter hero">
        <div className="hero-copy">
          <p className="kicker">Phys.io · an AI lab for passive cooling</p>
          <h1>A roof that gets <em>colder</em> than the air, at noon, with the power off.</h1>
          <p className="lede">
            The trick is a coating thinner than a soap bubble. It throws the sun back and lets the roof's own heat
            leak straight into space. Scroll to watch it happen. Every number below comes out of our simulator.
          </p>
          <div className="scroll-cue"><span />scroll</div>
        </div>
      </section>

      <section ref={set(1)} className="chapter right">
        <div className="card">
          <p className="ch">01 · the mirror</p>
          <h2>Sunlight is the enemy.</h2>
          <p>About a kilowatt of sunlight lands on every square metre. A silver mirror under the films sends almost all of it
             back. The amber dots are the sun: the ones that turn red and fade are the share the coating still absorbs.</p>
          <div className="figure">
            <span className="fig-n mono">{pct(sim?.solar_reflectance)}</span>
            <span className="fig-l">of sunlight reflected<br />by our featured design</span>
          </div>
          <p className="aside">Even the {pct(sim ? 1 - sim.solar_reflectance : undefined)} that is absorbed costs
             <b className="mono"> {w(sim?.p_sun_w_m2)} W/m²</b>. That is why every percent matters.</p>
        </div>
      </section>

      <section ref={set(2)} className="chapter left">
        <div className="card">
          <p className="ch">02 · the window</p>
          <h2>The sky has a hole in it.</h2>
          <p>Between 8 and 13 µm the atmosphere is nearly transparent. Heat radiated at those wavelengths does not come back:
             it goes to 3 K outer space. The ring is that window. Red dots are heat leaving the roof; the ones that turn
             ice-blue made it out, the rest are sent back by the air.</p>
          <div className="figure two">
            <div><span className="fig-n mono">{pct(sim?.window_emissivity)}</span><span className="fig-l">emissivity in the window</span></div>
            <div><span className="fig-n mono">{w(sim?.p_rad_w_m2, 0)}</span><span className="fig-l">W/m² radiated out</span></div>
          </div>
        </div>
      </section>

      <section ref={set(3)} className="chapter right">
        <div className="card">
          <p className="ch">03 · inside</p>
          <h2>Four films, two cheap materials.</h2>
          <p>Each layer is a few hundred nanometres. Their thicknesses decide which colours interfere and which escape.
             Get one wrong by 100 nm and the cooling can vanish.</p>
          <ol className="layers">
            {[...FEATURED.materials].map((m, i) => (
              <li key={i}><i style={{ background: materialInfo(m).color }} /> <span>{formula(m)}</span><span className="mono">{FEATURED.thicknesses_nm[i]} nm</span></li>
            )).reverse()}
            <li className="mirror"><i /> <span>{FEATURED.substrate} mirror</span><span className="mono">base</span></li>
          </ol>
          <div className="ledger mono" aria-label="Power balance">
            <span>{w(sim?.p_rad_w_m2)}</span><b>−</b><span>{w(sim?.p_atm_w_m2)}</span><b>−</b><span>{w(sim?.p_sun_w_m2)}</span><b>=</b>
            <span className="net">{w(sim?.p_net_w_m2, 2)}</span>
            <small>radiated</small><small /><small>sky back</small><small /><small>sun</small><small /><small>net W/m²</small>
          </div>
        </div>
      </section>

      <section ref={set(4)} className="chapter left">
        <div className="card">
          <p className="ch">04 · the search</p>
          <h2>Most guesses heat up.</h2>
          <p>These are {stats?.n ?? 36} random designs from the same space our agents search: up to five films of SiO₂, Al₂O₃,
             Si₃N₄, TiO₂ or MgF₂, 10 to 1000 nm each. Blue glows when it cools; a red bead means it warms the roof.</p>
          <div className="tally">
            <div><span className="fig-n mono">{stats ? stats.cool : "—"}</span><span className="fig-l">of {stats?.n ?? "—"} cool at all</span></div>
            <div><span className="fig-n mono">{stats ? stats.hit : "—"}</span><span className="fig-l">reach the {target ?? "—"} W/m² target</span></div>
          </div>
          <p className="aside">Range: <span className="mono">{w(stats?.min)}</span> to <span className="mono">{w(stats?.max)}</span> W/m².
             An AI lab earns its keep by reading each failure and proposing the next design on purpose, not at random.</p>
        </div>
      </section>

      <section ref={set(5)} className="chapter right last">
        <div className="card">
          <p className="ch">05 · your turn</p>
          <h2>Beat <span className="mono">{w(sim?.p_net_w_m2)}</span> W/m².</h2>
          <p>For scale: the famous 2014 Stanford coating simulates at <span className="mono">{w(control.sim)}</span> W/m² in
             our clear-sky model (they measured {control.pub ?? "—"} W/m² outdoors). Ours uses two cheap materials and fewer layers.</p>
          <div className="cta">
            <Link className="btn ink" to={`/design?d=${encodeDesign(FEATURED)}`}>Open this design</Link>
            <Link className="btn" to="/optimize">Let the optimizer try</Link>
            <Link className="btn" to="/runs">Read the lab's notebook</Link>
          </div>
          <p className="aside small">300 K, AM1.5 sun, analytic clear sky, transfer-matrix optics. <Link to="/methods">How we compute this</Link>.</p>
        </div>
      </section>
    </div>
  );
}
