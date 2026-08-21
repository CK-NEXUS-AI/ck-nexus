def productionAllowed (q10 q11 q12 provenance checksum : Bool) : Bool :=
  q10 && q11 && q12 && provenance && checksum

def externalWriteAllowed (governorApproved executionGrant : Bool) : Bool :=
  governorApproved && executionGrant

def swarmDispatchAllowed (withinBudget withinConcurrency : Bool) : Bool :=
  withinBudget && withinConcurrency

theorem production_blocked_without_q10
    (q11 q12 provenance checksum : Bool) :
    productionAllowed false q11 q12 provenance checksum = false := by
  simp [productionAllowed]

theorem production_blocked_without_q11
    (q10 q12 provenance checksum : Bool) :
    productionAllowed q10 false q12 provenance checksum = false := by
  simp [productionAllowed]

theorem production_blocked_without_q12
    (q10 q11 provenance checksum : Bool) :
    productionAllowed q10 q11 false provenance checksum = false := by
  simp [productionAllowed]

theorem production_blocked_without_provenance
    (q10 q11 q12 checksum : Bool) :
    productionAllowed q10 q11 q12 false checksum = false := by
  simp [productionAllowed]

theorem production_blocked_without_checksum
    (q10 q11 q12 provenance : Bool) :
    productionAllowed q10 q11 q12 provenance false = false := by
  simp [productionAllowed]

theorem external_write_requires_governor
    (executionGrant : Bool) :
    externalWriteAllowed false executionGrant = false := by
  simp [externalWriteAllowed]

theorem external_write_requires_grant
    (governorApproved : Bool) :
    externalWriteAllowed governorApproved false = false := by
  simp [externalWriteAllowed]

theorem swarm_dispatch_blocked_over_budget
    (withinConcurrency : Bool) :
    swarmDispatchAllowed false withinConcurrency = false := by
  simp [swarmDispatchAllowed]

theorem swarm_dispatch_blocked_over_concurrency
    (withinBudget : Bool) :
    swarmDispatchAllowed withinBudget false = false := by
  simp [swarmDispatchAllowed]
