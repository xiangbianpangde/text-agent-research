"""ResearchCTL canonical output layouts.

Each layout owns only its filesystem projection and freshness rules.  The
legacy layout remains implemented by :mod:`researchctl.indexer`.
"""

from .research_tool import (
    LayoutError,
    build_research_tool_index,
    generate_research_tool_index,
    reconcile_research_tool,
    research_tool_fingerprint,
)
from .research_tool_query import dispatch as dispatch_research_tool_query

__all__ = [
    "LayoutError",
    "build_research_tool_index",
    "generate_research_tool_index",
    "reconcile_research_tool",
    "research_tool_fingerprint",
    "dispatch_research_tool_query",
]
