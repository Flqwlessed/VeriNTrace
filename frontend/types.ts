export type Stance = 'supports' | 'refutes' | 'context';
export type ServiceStatus = 'available' | 'unavailable' | 'limited' | 'not_configured' | 'skipped' | 'demo';
export interface EvidenceSource {
 id: string; url: string | null; domain: string; publisher: string; title: string;
 publishedAt: string | null; sourceType: string; stance: Stance; confidence: number | null;
 excerpt: string; extraction: string; signals: string[];
}
export interface FactCheck {publisher: string; reviewedClaim: string; rating: string; publishedAt: string | null; url: string | null; match: string}
export interface GraphNode {id: string; type: 'claim' | 'article' | 'factcheck'; label: string; title: string; publisher: string; url: string | null; publishedAt: string | null; stance: Stance; confidence: number | null; excerpt: string}
export interface GraphEdge {source: string; target: string; relationship: string; isInferred: boolean; confidence: number; proof: string}
export interface Investigation {
 id: string; claim: string; originalInput: string; createdAt: string; demo: boolean; cached: boolean;
 status: string; verdict: string; confidence: string; explanation: string; citations: string[];
 services: Record<string, ServiceStatus>; warnings: string[]; evidence: EvidenceSource[]; factChecks: FactCheck[];
 graph: {nodes: GraphNode[]; edges: GraphEdge[]}; earliestSourceId: string | null; sourceGroups: number;
 independentSources: number | null; analyzedCount: number;
}
