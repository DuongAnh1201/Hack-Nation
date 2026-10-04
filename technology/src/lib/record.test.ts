import { describe, expect, it } from "vitest";
import recordText from "../../public/demo/record.jsonl?raw";
import { caption, keyMoments, labState, parseRecord } from "./record";

const entries = parseRecord(recordText);
const at = (id: string) => entries.findIndex((e) => e.id === id);

describe("record replay", () => {
  it("parses the demo record and rejects malformed lines", () => {
    expect(entries).toHaveLength(19);
    expect(() => parseRecord('{"id": "X1", "kind": "rumour"}')).toThrow(/Invalid record line/);
  });

  it("derives the final lab state", () => {
    const s = labState(entries, entries.length - 1);
    const status = Object.fromEntries(s.hypotheses.map((h) => [h.id, [h.status, h.decidedBy]]));
    expect(status).toMatchObject({ H1: ["supported", "V1"], H2: ["refuted", "V2"], H3: ["proposed", undefined], H4: ["supported", "V3"] });
    expect(s.control?.pNet).toBe(11.83);
    expect(s.best).toMatchObject({ experimentId: "E3", pNet: 56.66, materials: ["Si3N4", "SiO2", "Si3N4", "SiO2"] });
    expect(s.evaluations).toBe(101);
    expect(s.approvals).toBe(1);
    expect([s.firstRefuted, s.firstChange, s.firstFound]).toEqual([at("V2"), at("H4"), at("V3")]);
  });

  it("shows only what has happened so far", () => {
    const s = labState(entries, at("E2"));
    expect(s.hypotheses.find((h) => h.id === "H2")?.status).toBe("testing");
    expect(s.design?.experimentId).toBe("E2");
    expect(s.designResult).toBeUndefined();
    expect(s.best).toBeUndefined();
    expect(s.firstRefuted).toBeUndefined();
  });

  it("marks the key moments in story order", () => {
    expect(keyMoments(entries).map((m) => m.type)).toEqual(["control", "refuted", "changed", "supported", "approval"]);
  });

  it("writes a plain-language caption per entry", () => {
    expect(caption(entries[at("V2")])).toMatch(/^✗ H2 refuted: /);
    expect(caption(entries[at("R3")])).toBe("Result: 56.7 W/m² cooling, reflects 97.8% of sunlight");
  });
});
