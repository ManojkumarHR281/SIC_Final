"""Evidence records attached to deterministic and heuristic findings."""


def build_evidence(source, description, strength, verified=False, evidence_type="static_analysis"):
    return {"source": source, "description": description, "strength": strength, "verified": verified, "evidence_type": evidence_type}
