"""AgentOS Kernel — Cognitive operating system for Otto.

Implements the Reasoning Kernel architecture (arXiv 2602.20934v1):
- Reasoning Interrupt Cycle (RIC): save→load→process→align→restore
- Semantic Memory Management Unit (S-MMU): L1/L2/L3 paging
- Interrupt Vector Table (IVT): priority-driven event processing
- Cognitive Drift Detection: Δψ measurement and sync triggers
- Perception Alignment: LLM output validation

Preserves Otto's existing sophisticated features:
- HyMem dual-granularity retrieval (as L2 search strategy)
- ARAG blended retrieval (semantic+keyword+structured)
- FadeMem importance decay (feeds S-MMU importance scores)
- TraceMem episodic consolidation (runs during Sync Pulses)
- Procedural memory + trust scores (L2 procedural slice type)
- LATS/PreFlect/RL2F/ReflAct/MARS (preserved in agent prompts)
"""

from .types import InterruptType, Priority, InterruptStatus
from .state import CognitiveState
from .agents import KernelAgent, AgentConfig

__all__ = [
    "InterruptType",
    "Priority",
    "InterruptStatus",
    "CognitiveState",
    "KernelAgent",
    "AgentConfig",
]
