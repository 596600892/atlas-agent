"""
Atlas - 通用人工智能体

Atlas is built by all 14 specialized agents working together.
Each agent contributes its core capability module.

See: https://github.com/596600892/atlas-agent
"""

__version__ = "0.5.0"

from atlas_core.architecture import (
    # Phase 1: Core types
    AgentCapability,
    AgentManifest,
    AtlasMessage,
    ATLAS_MODULES,
    MessageType,
    MemoryEntry,
    RoutingDecision,
    LearningTask,
    LearningResult,
    verify_integrity,
    # Phase 4: Component system
    ArchComponent,
    ComponentState,
    ComponentRegistry,
    ComponentRegistryError,
    DependencyInjector,
    DependencyError,
    SystemBlueprint,
    PluginLoader,
    PluginLoadError,
    create_system,
)

from atlas_core.memory_engine import (
    MemoryStore,
    ImportanceScorer,
    PruningStrategy,
    ContextInjector,
    VectorSearch,
    MemoryConsolidator,
    MemoryEngine,
    create_memory_engine,
)

# Phase 5: Router Engine v2
from atlas_core.router_engine import (
    # Core types
    AgentManifest as RouterManifest,
    IntentResult,
    RoutingPlan,
    # Enums
    RouteLevel,
    ConfidenceLevel,
    FallbackStrategy,
    AggregationStrategy,
    # Classes
    IntentRouter,
    LLMEnhancer,
    RouterComponent,
    # Convenience
    create_router,
    route_query,
    create_router_component,
)
