import type { Card, Incident, Labels, Policy, Role, Sources } from "./lib";

export type Decision = { decision: "approved" | "rejected"; by: Role; at: number };
export type Ctx = {
  incidents: Incident[]; labels: Labels | null; policy: Policy | null; sources: Sources | null; card: Card | null;
  role: Role; decisions: Record<string, Decision>; decide: (id: string, d: Decision["decision"] | null) => void;
  stateOf: (i: Incident) => { text: string; pending: boolean; by?: string };
  roleOf: (ip: string) => string | undefined; nameOf: (ip: string) => string; famName: (f: string) => string;
  go: (page: Page, incident?: string) => void; selected: string | null; setSelected: (id: string | null) => void;
  now: number;
};
export type Page = "overview" | "incidents" | "network" | "labels" | "policy" | "model";
