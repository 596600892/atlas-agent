#!/usr/bin/env python3
"""
Atlas — 通用人工智能体 核心架构
================================

Phase 4: 运行时组件注册表 + 生命周期管理 + 依赖注入 + 系统蓝图 + 热插拔。

本文档定义了 Atlas Core 的接口契约，并提供运行时组件管理基础设施。
每个模块由不同的Agent团队开发，通过这里的接口定义统一协作。
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional, Callable


# ═══════════════════════════════════════════════
# 1. 基础类型
# ═══════════════════════════════════════════════


class ComponentState(Enum):
    """组件生命周期状态 / Component lifecycle state."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class MessageType(Enum):
    """消息类型 / Message types."""
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    VIDEO = "video"
    COMMAND = "command"
    EVENT = "event"
    ALERT = "alert"
    SYSTEM = "system"


class AgentCapability(Enum):
    """Agent能力标记 / Agent capability flags."""
    FINANCE_PREDICTION = "finance_prediction"
    SCREENPLAY_WRITING = "screenplay_writing"
    IMAGE_GENERATION = "image_generation"
    VIDEO_PRODUCTION = "video_production"
    MARKET_MONITORING = "market_monitoring"
    CROSS_DOMAIN_LEARNING = "cross_domain_learning"
    ECOMMERCE_OPS = "ecommerce_ops"
    SHORT_VIDEO_OPS = "short_video_ops"
    SWARM_SIMULATION = "swarm_simulation"
    SYSTEM_MONITORING = "system_monitoring"
    FAULT_ANALYSIS = "fault_analysis"
    TOKEN_MANAGEMENT = "token_management"
    CREATIVE_COORDINATION = "creative_coordination"
    TASK_ORCHESTRATION = "task_orchestration"
    MEMORY_MANAGEMENT = "memory_management"
    VOICE_INTERACTION = "voice_interaction"
    ARCHITECTURE = "architecture"
    PLUGIN = "plugin"


@dataclass
class AtlasMessage:
    """Atlas内部统一消息格式 / Unified message format."""
    msg_id: str
    type: MessageType
    content: Any
    source: str
    target: Optional[str] = None
    timestamp: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentManifest:
    """Agent注册信息 / Agent registration info."""
    name: str
    version: str
    capabilities: list[AgentCapability]
    description: str
    repo_url: str
    requires: list[str] = field(default_factory=list)


@dataclass
class RoutingDecision:
    """路由决策结果 / Routing decision."""
    intent: str
    primary_agent: str
    confidence: float
    supporting_agents: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)


@dataclass
class MemoryEntry:
    """记忆条目 / Memory entry."""
    key: str
    content: str
    type: str
    timestamp: float
    ttl: Optional[int] = None
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5


@dataclass
class LearningTask:
    """学习任务 / Learning task."""
    domain: str
    objective: str
    priority: int = 0
    max_duration: int = 300
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class LearningResult:
    """学习结果 / Learning result."""
    task: LearningTask
    learned: bool
    key_insights: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    validated: bool = False
    open_sourced: bool = False
    error: Optional[str] = None


# ═══════════════════════════════════════════════
# 2. 组件接口 — 所有Atlas组件的基础类
# ═══════════════════════════════════════════════


class ArchComponent:
    """Atlas 架构组件基类 / Base class for all Atlas architecture components.

    提供标准生命周期管理，支持热插拔。
    所有核心模块（Voice、Memory、Router 等）都应继承此类。
    """

    def __init__(self, name: str, version: str = "1.0.0",
                 description: str = "", requires: list[str] = None):
        self.name = name
        self.version = version
        self.description = description
        self.requires = requires or []
        self._state = ComponentState.UNINITIALIZED
        self._state_history: list[tuple[ComponentState, float]] = []
        self._errors: list[str] = []
        self._start_time: float = 0.0
        self._component_id: str = uuid.uuid4().hex[:12]

    @property
    def state(self) -> ComponentState:
        return self._state

    @property
    def component_id(self) -> str:
        return self._component_id

    @property
    def uptime(self) -> float:
        if self._state == ComponentState.RUNNING and self._start_time > 0:
            return time.time() - self._start_time
        return 0.0

    @property
    def status(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "component_id": self._component_id,
            "state": self._state.value,
            "uptime": round(self.uptime, 2),
            "requires": self.requires,
            "errors": self._errors[-3:] if self._errors else [],
        }

    def _transition(self, new_state: ComponentState) -> None:
        """安全的状态转换 / Safe state transition."""
        self._state = new_state
        self._state_history.append((new_state, time.time()))

    def init(self) -> bool:
        """初始化组件 / Initialize component.
        
        Returns:
            bool: True 表示初始化成功
        """
        if self._state != ComponentState.UNINITIALIZED:
            return True
        self._transition(ComponentState.INITIALIZING)
        try:
            result = self._do_init()
            if result:
                self._transition(ComponentState.RUNNING)
                self._start_time = time.time()
            else:
                self._transition(ComponentState.ERROR)
            return result
        except Exception as e:
            self._errors.append(f"init: {e}")
            self._transition(ComponentState.ERROR)
            return False

    def _do_init(self) -> bool:
        """子类重写此方法实现自定义初始化 /
        Subclass hook for custom initialization."""
        return True

    def shutdown(self) -> bool:
        """关闭组件 / Shutdown component.
        
        Returns:
            bool: True 表示关闭成功
        """
        if self._state not in (ComponentState.RUNNING, ComponentState.ERROR):
            return True
        self._transition(ComponentState.STOPPING)
        try:
            result = self._do_shutdown()
            self._transition(ComponentState.STOPPED)
            return result
        except Exception as e:
            self._errors.append(f"shutdown: {e}")
            self._transition(ComponentState.STOPPED)
            return False

    def _do_shutdown(self) -> bool:
        """子类重写此方法实现自定义关闭 /
        Subclass hook for custom shutdown."""
        return True

    def restart(self) -> bool:
        """重启组件 / Restart component."""
        self.shutdown()
        # Reset to uninitialized so init() can run fresh
        self._state = ComponentState.UNINITIALIZED
        return self.init()

    def health(self) -> dict:
        """健康检查 / Health check.
        
        Returns:
            dict: {"healthy": bool, "state": str, "uptime": float, "errors": list}
        """
        return {
            "healthy": self._state == ComponentState.RUNNING,
            "state": self._state.value,
            "uptime": round(self.uptime, 2),
            "errors": self._errors[-3:] if self._errors else [],
            "component_id": self._component_id,
            "name": self.name,
        }


# ═══════════════════════════════════════════════
# 3. 组件注册表 — 运行时热插拔
# ═══════════════════════════════════════════════


class ComponentRegistryError(Exception):
    """组件注册表错误 / Registry error."""
    pass


class ComponentRegistry:
    """运行时组件注册表，支持热插拔。

    所有 Atlas 组件在此注册，通过名称检索。
    支持运行时注册/注销，自动依赖校验。
    """

    def __init__(self):
        self._components: dict[str, ArchComponent] = {}
        self._lock = False  # 简单防重复注册

    @property
    def count(self) -> int:
        return len(self._components)

    def register(self, component: ArchComponent) -> bool:
        """注册一个组件 / Register a component (hot-plug).

        Args:
            component: 要注册的组件实例

        Returns:
            bool: True 表示注册成功

        Raises:
            ComponentRegistryError: 组件名重复
        """
        if component.name in self._components:
            raise ComponentRegistryError(
                f"Component '{component.name}' already registered"
            )
        self._components[component.name] = component
        return True

    def unregister(self, name: str) -> bool:
        """注销一个组件 / Unregister a component (hot-unplug).

        在注销前会检查是否有其他组件依赖此组件。
        
        Args:
            name: 组件名

        Returns:
            bool: True 表示注销成功

        Raises:
            ComponentRegistryError: 有其他组件依赖此组件
        """
        if name not in self._components:
            return False

        # 检查依赖 — 是否有组件依赖这个要注销的组件
        dependents = []
        for c_name, comp in self._components.items():
            if c_name != name and name in comp.requires:
                dependents.append(c_name)
        if dependents:
            raise ComponentRegistryError(
                f"Cannot unregister '{name}': depended on by {dependents}"
            )

        comp = self._components.pop(name)
        if comp.state in (ComponentState.RUNNING, ComponentState.ERROR):
            comp.shutdown()
        return True

    def get(self, name: str) -> Optional[ArchComponent]:
        """按名称获取组件 / Get component by name."""
        return self._components.get(name)

    def list(self) -> list[dict]:
        """列出所有已注册组件及其状态 /
        List all registered components with status."""
        return [c.status for c in self._components.values()]

    def find_by_capability(self, capability: str) -> list[ArchComponent]:
        """按能力查找组件 / Find components by capability name.
        
        通过模块的 description 或 status 中的信息判断。
        主要用于蓝图能力映射查找。
        """
        results = []
        for comp in self._components.values():
            if capability.lower() in comp.description.lower():
                results.append(comp)
        return results

    def has(self, name: str) -> bool:
        """检查组件是否已注册 / Check if component is registered."""
        return name in self._components

    def clear(self) -> None:
        """清空注册表 / Clear all components."""
        for comp in self._components.values():
            if comp.state in (ComponentState.RUNNING, ComponentState.ERROR):
                comp.shutdown()
        self._components.clear()

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """获取依赖关系图 / Get dependency graph.
        
        Returns:
            dict: {component_name: [dependency_names]}
        """
        return {name: comp.requires for name, comp in self._components.items()}


# ═══════════════════════════════════════════════
# 4. 依赖注入器 — 自动解析依赖关系
# ═══════════════════════════════════════════════


class DependencyError(Exception):
    """依赖注入错误 / Dependency error."""
    pass


class DependencyInjector:
    """依赖注入器 — 自动解析组件依赖关系。

    支持拓扑排序启动、环形依赖检测、自动注入依赖组件引用。
    """

    def __init__(self, registry: ComponentRegistry):
        self._registry = registry
        self._start_order: list[str] = []

    def resolve_order(self) -> list[str]:
        """拓扑排序确定组件启动顺序 /
        Topological sort to determine start order.

        Returns:
            list[str]: 按依赖顺序排列的组件名称列表

        Raises:
            DependencyError: 存在环形依赖
        """
        graph = self._registry.get_dependency_graph()

        # Kahn 算法拓扑排序
        in_degree: dict[str, int] = {n: 0 for n in graph}
        for name, deps in graph.items():
            for dep in deps:
                if dep not in graph:
                    raise DependencyError(
                        f"Component '{name}' requires unknown '{dep}'"
                    )
                in_degree[name] = in_degree.get(name, 0) + 1

        # 入度=0 的节点（无依赖）优先
        queue = [n for n, d in in_degree.items() if d == 0]
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            # 查找哪些节点依赖当前节点
            for name, deps in graph.items():
                if node in deps:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(order) != len(graph):
            # 还有节点未排序 = 环形依赖
            unresolved = set(graph.keys()) - set(order)
            raise DependencyError(f"Circular dependency detected: {unresolved}")

        self._start_order = order
        return order

    def inject(self, component: ArchComponent) -> dict[str, ArchComponent]:
        """为组件注入其依赖的引用 /
        Inject dependency references into a component.

        Args:
            component: 需要注入依赖的组件

        Returns:
            dict[str, ArchComponent]: {dependency_name: component_instance}
        """
        deps = {}
        for dep_name in component.requires:
            dep = self._registry.get(dep_name)
            if dep is None:
                raise DependencyError(
                    f"Required dependency '{dep_name}' for "
                    f"'{component.name}' not found"
                )
            deps[dep_name] = dep

        # 如果组件有 set_dependencies 方法，自动注入
        if hasattr(component, "set_dependencies") and callable(
            getattr(component, "set_dependencies")
        ):
            component.set_dependencies(deps)

        return deps

    def init_all(self) -> list[dict]:
        """按依赖顺序初始化所有组件 /
        Initialize all components in dependency order.

        Returns:
            list[dict]: 每个组件的初始化结果列表
        """
        order = self.resolve_order()
        results = []
        for name in order:
            comp = self._registry.get(name)
            if comp is None:
                results.append({"name": name, "success": False, "error": "not found"})
                continue
            # 先注入依赖
            try:
                self.inject(comp)
            except DependencyError as e:
                results.append({"name": name, "success": False, "error": str(e)})
                continue
            success = comp.init()
            results.append({
                "name": name,
                "success": success,
                "state": comp.state.value,
            })
        return results

    def shutdown_all(self) -> list[dict]:
        """按依赖逆序关闭所有组件 /
        Shutdown all components in reverse dependency order.

        Returns:
            list[dict]: 每个组件的关闭结果列表
        """
        order = self.resolve_order()[::-1]  # 逆序关闭
        results = []
        for name in order:
            comp = self._registry.get(name)
            if comp is None:
                continue
            success = comp.shutdown()
            results.append({
                "name": name,
                "success": success,
                "state": comp.state.value,
            })
        return results


# ═══════════════════════════════════════════════
# 5. 系统蓝图 — 完整拓扑导出
# ═══════════════════════════════════════════════


class SystemBlueprint:
    """系统蓝图 — 从组件注册表导出完整系统拓扑。

    用于 CLI、Dashboard 展示、系统文档生成。
    """

    def __init__(self, registry: ComponentRegistry,
                 dep_injector: DependencyInjector):
        self._registry = registry
        self._dep_injector = dep_injector

    def to_dict(self) -> dict:
        """导出完整系统拓扑为字典 /
        Export full system topology as dict.

        Returns:
            dict: {
                "atlas_version": str,
                "total_components": int,
                "components": [...],
                "edges": [...],
                "dependencies": {...},
                "start_order": [...],
            }
        """
        graph = self._registry.get_dependency_graph()

        # 节点列表
        nodes = []
        for name, comp in self._registry._components.items():
            nodes.append(comp.status)

        # 边列表（依赖关系可视化用）
        edges = []
        for name, deps in graph.items():
            for dep in deps:
                edges.append({
                    "from": dep,
                    "to": name,
                    "type": "depends_on",
                })

        # 启动顺序
        start_order = []
        try:
            start_order = self._dep_injector.resolve_order()
        except DependencyError:
            start_order = ["(circular dependency detected)"]

        return {
            "atlas_version": "0.4.0",
            "exported_at": time.time(),
            "total_components": self._registry.count,
            "components": nodes,
            "edges": edges,
            "dependencies": graph,
            "start_order": start_order,
        }

    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON 字符串 / Export as JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def summary(self) -> str:
        """生成人类可读的系统摘要 /
        Generate human-readable system summary."""
        data = self.to_dict()
        lines = [
            f"Atlas {data['atlas_version']} — System Blueprint",
            f"{'=' * 50}",
            f"Total components: {data['total_components']}",
            f"Components:",
        ]
        for comp in data["components"]:
            state_mark = "✓" if comp["state"] == "running" else "○"
            lines.append(
                f"  {state_mark} {comp['name']} v{comp['version']} "
                f"[{comp['state']}]"
            )
        lines.append(f"\nDependency edges: {len(data['edges'])}")
        lines.append(f"Start order: {' → '.join(data['start_order'][:10])}")
        if len(data["start_order"]) > 10:
            lines[-1] += f" and {len(data['start_order']) - 10} more"
        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 6. 插件加载器 — 热加载外部模块
# ═══════════════════════════════════════════════


class PluginLoadError(Exception):
    """插件加载错误 / Plugin load error."""
    pass


class PluginLoader:
    """插件加载器 — 从目录动态加载外部模块作为组件。

    扫描指定目录中的 Python 模块，自动注册 ArchComponent 子类。
    支持热加载（运行时加载新插件）。
    """

    def __init__(self, registry: ComponentRegistry,
                 plugin_dirs: list[str] = None):
        """
        Args:
            registry: 组件注册表
            plugin_dirs: 插件扫描目录列表
        """
        self._registry = registry
        self._plugin_dirs = plugin_dirs or []
        self._loaded_plugins: dict[str, str] = {}  # name → module path

    def add_plugin_dir(self, path: str) -> None:
        """添加插件扫描目录 / Add a plugin directory."""
        abs_path = os.path.abspath(path)
        if abs_path not in self._plugin_dirs:
            self._plugin_dirs.append(abs_path)

    def scan_and_load(self) -> list[dict]:
        """扫描插件目录并加载所有组件 /
        Scan plugin directories and load all components.

        Returns:
            list[dict]: 每个插件的加载结果
        """
        results = []
        for plugin_dir in self._plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue
            for fname in sorted(os.listdir(plugin_dir)):
                if fname.endswith(".py") and not fname.startswith("_"):
                    module_path = os.path.join(plugin_dir, fname)
                    result = self._load_module(module_path)
                    results.append(result)
        return results

    def _load_module(self, module_path: str) -> dict:
        """加载单个 Python 模块并注册其中的组件 /
        Load a single Python module and register contained components."""
        name = os.path.splitext(os.path.basename(module_path))[0]
        result = {
            "module": name,
            "path": module_path,
            "success": False,
            "components_found": 0,
            "components_registered": 0,
            "error": None,
        }

        try:
            # 将插件目录加入 sys.path
            plugin_dir = os.path.dirname(module_path)
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)

            # 导入模块
            spec = importlib.util.spec_from_file_location(name, module_path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Could not load spec for {module_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找 ArchComponent 子类
            components_found = 0
            components_registered = 0
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, ArchComponent)
                        and attr is not ArchComponent):
                    components_found += 1
                    # 检查是否有无参构造函数可供实例化
                    try:
                        component = attr()
                        self._registry.register(component)
                        components_registered += 1
                        self._loaded_plugins[component.name] = module_path
                    except ComponentRegistryError:
                        pass  # 重复注册跳过
                    except Exception as e:
                        result["error"] = (
                            f"Cannot instantiate {attr_name}: {e}"
                        )

            result["success"] = True
            result["components_found"] = components_found
            result["components_registered"] = components_registered

        except Exception as e:
            result["error"] = str(e)

        return result

    def load_single(self, module_path: str) -> dict:
        """加载单个插件文件 / Load a single plugin file."""
        return self._load_module(module_path)

    def list_plugins(self) -> dict[str, str]:
        """列出已加载的插件 / List loaded plugins."""
        return dict(self._loaded_plugins)


# ═══════════════════════════════════════════════
# 7. 核心集成图 — 模块定义与完整性验证
# ═══════════════════════════════════════════════

ATLAS_MODULES = {
    "voice_engine": {
        "lead_agent": "ceo-orchestrator",
        "description": "语音识别与合成，自然对话驱动",
        "depends_on": [],
        "contributes": [AgentCapability.VOICE_INTERACTION],
    },
    "memory_engine": {
        "lead_agent": "system-sentinel",
        "description": "持久记忆、跨会话检索",
        "depends_on": [],
        "contributes": [AgentCapability.MEMORY_MANAGEMENT],
    },
    "learn_engine": {
        "lead_agent": "cross-domain-learner",
        "description": "Idle-Learning循环，自学→验证→固化→开源",
        "depends_on": ["memory_engine"],
        "contributes": [AgentCapability.CROSS_DOMAIN_LEARNING],
    },
    "router_engine": {
        "lead_agent": "ceo-orchestrator",
        "description": "意图识别→Agent路由→结果聚合",
        "depends_on": [],
        "contributes": [AgentCapability.TASK_ORCHESTRATION],
    },
    "finance_module": {
        "lead_agent": "finance-agent",
        "description": "8维股票预测、因子分析",
        "depends_on": [],
        "contributes": [AgentCapability.FINANCE_PREDICTION],
    },
    "creative_module": {
        "lead_agent": "creative-coordinator",
        "description": "剧本/图像/视频创作管线编排",
        "depends_on": [],
        "contributes": [AgentCapability.CREATIVE_COORDINATION],
    },
    "monitor_module": {
        "lead_agent": "market-monitor",
        "description": "市场监控、风险预警",
        "depends_on": [],
        "contributes": [AgentCapability.MARKET_MONITORING],
    },
    "swarm_module": {
        "lead_agent": "mirofish-simulator",
        "description": "群体智能模拟、预测聚合",
        "depends_on": [],
        "contributes": [AgentCapability.SWARM_SIMULATION],
    },
    "ops_module": {
        "lead_agent": "deerflow-orchestrator",
        "description": "系统运维、故障恢复",
        "depends_on": [],
        "contributes": [AgentCapability.FAULT_ANALYSIS],
    },
    "sentinel_module": {
        "lead_agent": "system-sentinel",
        "description": "服务健康监控",
        "depends_on": [],
        "contributes": [AgentCapability.SYSTEM_MONITORING],
    },
    "budget_module": {
        "lead_agent": "token-budget-agent",
        "description": "Token预算管理",
        "depends_on": [],
        "contributes": [AgentCapability.TOKEN_MANAGEMENT],
    },
    "architecture_module": {
        "lead_agent": "ceo-orchestrator",
        "description": "组件注册表、依赖注入、系统蓝图、热插拔",
        "depends_on": [],
        "contributes": [AgentCapability.ARCHITECTURE],
    },
}

ARCHITECTURE_DESCRIPTION = (
    "Atlas Architecture — Component Registry, "
    "Dependency Injection, Hot-Plug System, System Blueprint"
)


def verify_integrity() -> list[str]:
    """验证所有模块依赖是否完整 /
    Verify all module dependencies are complete."""
    errors = []
    all_contributions = set()
    for mod_name, mod in ATLAS_MODULES.items():
        for cap in mod["contributes"]:
            all_contributions.add(cap)
        for dep in mod["depends_on"]:
            if dep not in ATLAS_MODULES:
                errors.append(f"{mod_name} depends on unknown module: {dep}")
    return errors


# ═══════════════════════════════════════════════
# 8. 便利工厂函数
# ═══════════════════════════════════════════════


def create_system() -> tuple[ComponentRegistry, DependencyInjector,
                              SystemBlueprint, PluginLoader]:
    """创建完整 Atlas 系统基础设施 /
    Create complete Atlas system infrastructure.

    Returns:
        tuple: (registry, injector, blueprint, plugin_loader)
    """
    registry = ComponentRegistry()
    injector = DependencyInjector(registry)
    blueprint = SystemBlueprint(registry, injector)
    plugin_loader = PluginLoader(registry)
    return registry, injector, blueprint, plugin_loader


# ═══════════════════════════════════════════════
# 9. 快速验证
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    errors = verify_integrity()
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
    else:
        print("Atlas architecture integrity check: PASSED")
        print(f"Total modules: {len(ATLAS_MODULES)}")
        print(f"Total capabilities: "
              f"{len(set(c for m in ATLAS_MODULES.values() for c in m['contributes']))}")

    # 演示组件注册表
    registry, injector, blueprint, _ = create_system()

    # 注册一个演示组件
    class DemoComponent(ArchComponent):
        pass

    registry.register(DemoComponent("demo", "1.0.0", "Demo component"))
    injector.init_all()

    print(f"\nSystem blueprint:")
    print(blueprint.summary())
    print(f"\nJSON preview:")
    print(blueprint.to_json(indent=2)[:500])
