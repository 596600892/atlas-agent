"""
Atlas Phase 4: 架构模块测试
Architecture module tests.
"""

import tempfile
import os
import json
import time

import pytest

from atlas_core.architecture import (
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
    verify_integrity,
    MessageType,
    AgentCapability,
)


# ══════════════════════════════════════════════════════════════
# 测试辅助组件 / Test helper components
# ══════════════════════════════════════════════════════════════


class SimpleComponent(ArchComponent):
    """无依赖的简单组件 / Simple component with no dependencies."""
    pass


class FailingInitComponent(ArchComponent):
    """初始化失败的组件 / Component that fails on init."""
    def _do_init(self) -> bool:
        return False


class CrashingInitComponent(ArchComponent):
    """初始化抛异常的组件 / Component that crashes on init."""
    def _do_init(self) -> bool:
        raise RuntimeError("Init crashed intentionally")


class ComponentWithDeps(ArchComponent):
    """有依赖的组件 / Component with dependencies."""
    def __init__(self, name="has_deps", requires=None, **kwargs):
        super().__init__(name, requires=requires or ["base"], **kwargs)
        self.injected_deps = {}

    def set_dependencies(self, deps):
        self.injected_deps = deps


# ══════════════════════════════════════════════════════════════
# ArchComponent 生命周期测试
# ══════════════════════════════════════════════════════════════


class TestArchComponentLifecycle:
    """组件生命周期测试 / Component lifecycle tests."""

    def test_initial_state(self):
        """初始状态为 UNINITIALIZED / Initial state is UNINITIALIZED."""
        comp = SimpleComponent("test")
        assert comp.state == ComponentState.UNINITIALIZED

    def test_init_success(self):
        """初始化成功 / Successful init."""
        comp = SimpleComponent("test")
        assert comp.init() is True
        assert comp.state == ComponentState.RUNNING

    def test_init_already_running(self):
        """重复初始化不影响 / Re-init on running component is no-op."""
        comp = SimpleComponent("test")
        comp.init()
        assert comp.init() is True
        assert comp.state == ComponentState.RUNNING

    def test_init_failure(self):
        """初始化失败 / Failed init."""
        comp = FailingInitComponent("test")
        assert comp.init() is False
        assert comp.state == ComponentState.ERROR

    def test_init_crash(self):
        """初始化抛异常 / Init raises exception."""
        comp = CrashingInitComponent("test")
        assert comp.init() is False
        assert comp.state == ComponentState.ERROR

    def test_shutdown(self):
        """正常关闭 / Normal shutdown."""
        comp = SimpleComponent("test")
        comp.init()
        assert comp.shutdown() is True
        assert comp.state == ComponentState.STOPPED

    def test_shutdown_from_error(self):
        """从错误状态关闭 / Shutdown from error state."""
        comp = FailingInitComponent("test")
        comp.init()
        assert comp.shutdown() is True
        assert comp.state == ComponentState.STOPPED

    def test_shutdown_uninitialized(self):
        """未初始化关闭是安全操作 / Shutdown uninitialized is safe."""
        comp = SimpleComponent("test")
        assert comp.shutdown() is True  # uninitialized shutdown returns True

    def test_restart(self):
        """重启组件 / Restart component."""
        comp = SimpleComponent("test")
        comp.init()
        assert comp.state == ComponentState.RUNNING
        assert comp.restart() is True
        assert comp.state == ComponentState.RUNNING

    def test_uptime(self):
        """运行时间计算 / Uptime calculation."""
        comp = SimpleComponent("test")
        assert comp.uptime == 0.0
        comp.init()
        assert comp.uptime > 0.0

    def test_health_running(self):
        """运行中的健康检查 / Health check when running."""
        comp = SimpleComponent("test")
        comp.init()
        health = comp.health()
        assert health["healthy"] is True
        assert health["state"] == "running"

    def test_health_uninitialized(self):
        """未初始化的健康检查 / Health check when uninitialized."""
        comp = SimpleComponent("test")
        health = comp.health()
        assert health["healthy"] is False
        assert health["state"] == "uninitialized"

    def test_status_fields(self):
        """状态信息字段完整 / Status fields are complete."""
        comp = SimpleComponent("test_comp")
        comp.init()
        status = comp.status
        assert status["name"] == "test_comp"
        assert status["state"] == "running"
        assert status["component_id"] == comp.component_id

    def test_component_id_unique(self):
        """每个组件有唯一 ID / Each component gets a unique ID."""
        c1 = SimpleComponent("a")
        c2 = SimpleComponent("b")
        assert c1.component_id != c2.component_id


# ══════════════════════════════════════════════════════════════
# ComponentRegistry 测试
# ══════════════════════════════════════════════════════════════


class TestComponentRegistry:
    """组件注册表测试 / Component registry tests."""

    def test_register(self):
        """注册组件 / Register a component."""
        registry = ComponentRegistry()
        comp = SimpleComponent("test")
        assert registry.register(comp) is True
        assert registry.count == 1

    def test_register_duplicate(self):
        """重复注册抛异常 / Duplicate registration raises error."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("test"))
        with pytest.raises(ComponentRegistryError):
            registry.register(SimpleComponent("test"))

    def test_unregister(self):
        """注销组件 / Unregister a component."""
        registry = ComponentRegistry()
        comp = SimpleComponent("test")
        registry.register(comp)
        assert registry.unregister("test") is True
        assert registry.count == 0

    def test_unregister_nonexistent(self):
        """注销不存在的组件返回 False / Unregister nonexistent returns False."""
        registry = ComponentRegistry()
        assert registry.unregister("missing") is False

    def test_unregister_with_dependents(self):
        """注销有依赖的组件抛异常 / Unregister with dependents raises."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("base"))
        registry.register(ComponentWithDeps("top", requires=["base"]))
        with pytest.raises(ComponentRegistryError) as exc:
            registry.unregister("base")
        assert "depended on by" in str(exc.value).lower()

    def test_get(self):
        """获取组件 / Get component."""
        registry = ComponentRegistry()
        comp = SimpleComponent("test")
        registry.register(comp)
        assert registry.get("test") is comp

    def test_get_missing(self):
        """获取不存在的组件返回 None / Get missing returns None."""
        registry = ComponentRegistry()
        assert registry.get("missing") is None

    def test_has(self):
        """检查组件存在 / Check component existence."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("test"))
        assert registry.has("test") is True
        assert registry.has("missing") is False

    def test_list(self):
        """列出所有组件 / List all components."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("a"))
        registry.register(SimpleComponent("b"))
        listing = registry.list()
        assert len(listing) == 2
        names = [c["name"] for c in listing]
        assert "a" in names
        assert "b" in names

    def test_clear(self):
        """清空注册表 / Clear registry."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("a"))
        registry.register(SimpleComponent("b"))
        registry.clear()
        assert registry.count == 0

    def test_get_dependency_graph(self):
        """获取依赖关系图 / Get dependency graph."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("a"))
        registry.register(ComponentWithDeps("b", requires=["a"]))
        graph = registry.get_dependency_graph()
        assert graph["a"] == []
        assert graph["b"] == ["a"]


# ══════════════════════════════════════════════════════════════
# DependencyInjector 测试
# ══════════════════════════════════════════════════════════════


class TestDependencyInjector:
    """依赖注入器测试 / Dependency injector tests."""

    def test_resolve_simple_order(self):
        """简单拓扑排序 / Simple topological sort."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("a"))
        registry.register(ComponentWithDeps("b", requires=["a"]))
        injector = DependencyInjector(registry)
        order = injector.resolve_order()
        # a 必须在 b 之前
        assert order.index("a") < order.index("b")

    def test_resolve_complex_order(self):
        """复杂依赖排序 / Complex dependency ordering."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("base"))
        registry.register(ComponentWithDeps("middle", requires=["base"]))
        registry.register(ComponentWithDeps("top", requires=["middle", "base"]))
        injector = DependencyInjector(registry)
        order = injector.resolve_order()
        assert order.index("base") < order.index("middle")
        assert order.index("middle") < order.index("top")

    def test_circular_dependency(self):
        """环形依赖检测 / Circular dependency detection."""
        registry = ComponentRegistry()
        registry.register(ComponentWithDeps("a", requires=["b"]))
        registry.register(ComponentWithDeps("b", requires=["a"]))
        injector = DependencyInjector(registry)
        with pytest.raises(DependencyError) as exc:
            injector.resolve_order()
        assert "circular" in str(exc.value).lower()

    def test_missing_dependency(self):
        """缺失依赖检测 / Missing dependency detection."""
        registry = ComponentRegistry()
        registry.register(ComponentWithDeps("a", requires=["missing_dep"]))
        injector = DependencyInjector(registry)
        with pytest.raises(DependencyError):
            injector.resolve_order()

    def test_injection(self):
        """依赖注入 / Dependency injection."""
        registry = ComponentRegistry()
        base = SimpleComponent("base")
        registry.register(base)
        top = ComponentWithDeps("top", requires=["base"])
        registry.register(top)
        injector = DependencyInjector(registry)
        deps = injector.inject(top)
        assert "base" in deps
        assert deps["base"] is base
        assert top.injected_deps["base"] is base

    def test_init_all(self):
        """按依赖顺序初始化所有组件 / Init all in dependency order."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("base"))
        registry.register(ComponentWithDeps("top", requires=["base"]))
        injector = DependencyInjector(registry)
        results = injector.init_all()
        assert len(results) == 2
        assert all(r["success"] for r in results)
        # 确保 base 在 top 之前初始化
        base_result = [r for r in results if r["name"] == "base"][0]
        top_result = [r for r in results if r["name"] == "top"][0]
        assert results.index(base_result) < results.index(top_result)

    def test_shutdown_all(self):
        """按依赖逆序关闭所有组件 / Shutdown all in reverse order."""
        registry = ComponentRegistry()
        registry.register(SimpleComponent("base"))
        registry.register(ComponentWithDeps("top", requires=["base"]))
        injector = DependencyInjector(registry)
        injector.init_all()
        results = injector.shutdown_all()
        assert len(results) == 2


# ══════════════════════════════════════════════════════════════
# SystemBlueprint 测试
# ══════════════════════════════════════════════════════════════


class TestSystemBlueprint:
    """系统蓝图测试 / System blueprint tests."""

    def test_to_dict_basic(self):
        """导出基本蓝图 / Export basic blueprint."""
        registry, injector, blueprint, _ = create_system()
        registry.register(SimpleComponent("test"))
        data = blueprint.to_dict()
        assert "atlas_version" in data
        assert "total_components" in data
        assert data["total_components"] == 1
        assert "components" in data
        assert "edges" in data
        assert "dependencies" in data
        assert "start_order" in data

    def test_to_dict_with_deps(self):
        """带依赖的蓝图 / Blueprint with dependencies."""
        registry, injector, blueprint, _ = create_system()
        registry.register(SimpleComponent("base"))
        registry.register(ComponentWithDeps("top", requires=["base"]))
        data = blueprint.to_dict()
        assert data["total_components"] == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["to"] == "top"

    def test_to_json(self):
        """导出 JSON / Export as JSON."""
        registry, injector, blueprint, _ = create_system()
        registry.register(SimpleComponent("test"))
        json_str = blueprint.to_json()
        data = json.loads(json_str)
        assert data["total_components"] == 1

    def test_summary(self):
        """摘要文本 / Summary text."""
        registry, injector, blueprint, _ = create_system()
        registry.register(SimpleComponent("test"))
        summary = blueprint.summary()
        assert "System Blueprint" in summary
        assert "Total components: 1" in summary
        assert "test" in summary


# ══════════════════════════════════════════════════════════════
# PluginLoader 测试
# ══════════════════════════════════════════════════════════════


class TestPluginLoader:
    """插件加载器测试 / Plugin loader tests."""

    def test_scan_and_load_empty_dir(self):
        """扫描空目录 / Scan empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = ComponentRegistry()
            loader = PluginLoader(registry, [tmpdir])
            results = loader.scan_and_load()
            assert len(results) == 0

    def test_load_single(self):
        """加载单个插件 / Load a single plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_code = """
from atlas_core.architecture import ArchComponent

class PluginA(ArchComponent):
    def __init__(self):
        super().__init__("plugin_a", "1.0.0", "Test plugin A")
"""
            plugin_path = os.path.join(tmpdir, "plugin_a.py")
            with open(plugin_path, "w") as f:
                f.write(plugin_code)

            registry = ComponentRegistry()
            loader = PluginLoader(registry)
            result = loader.load_single(plugin_path)
            assert result["success"] is True
            assert result["components_found"] >= 1
            assert result["components_registered"] >= 1
            assert registry.has("plugin_a") is True

    def test_scan_and_load_multiple(self):
        """扫描并加载多个插件 / Scan and load multiple plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["alpha", "beta"]:
                plugin_code = f"""
from atlas_core.architecture import ArchComponent

class Plugin{name.capitalize()}(ArchComponent):
    def __init__(self):
        super().__init__("{name}", "1.0.0", "Plugin {name}")
"""
                with open(os.path.join(tmpdir, f"{name}.py"), "w") as f:
                    f.write(plugin_code)

            registry = ComponentRegistry()
            loader = PluginLoader(registry, [tmpdir])
            results = loader.scan_and_load()
            assert len(results) == 2
            assert registry.count == 2
            assert registry.has("alpha") is True
            assert registry.has("beta") is True

    def test_invalid_module(self):
        """加载无效模块 / Load invalid module."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = os.path.join(tmpdir, "broken.py")
            with open(plugin_path, "w") as f:
                f.write("this is not valid python @@")

            registry = ComponentRegistry()
            loader = PluginLoader(registry)
            result = loader.load_single(plugin_path)
            assert result["success"] is False

    def test_list_plugins(self):
        """列出已加载插件 / List loaded plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_code = """
from atlas_core.architecture import ArchComponent

class PluginX(ArchComponent):
    def __init__(self):
        super().__init__("plugin_x", "1.0.0", "Plugin X")
"""
            plugin_path = os.path.join(tmpdir, "plugin_x.py")
            with open(plugin_path, "w") as f:
                f.write(plugin_code)

            registry = ComponentRegistry()
            loader = PluginLoader(registry)
            loader.load_single(plugin_path)
            plugins = loader.list_plugins()
            assert "plugin_x" in plugins

    def test_add_plugin_dir(self):
        """添加插件目录 / Add plugin directory."""
        registry = ComponentRegistry()
        loader = PluginLoader(registry)
        loader.add_plugin_dir("/tmp/plugins")
        assert "/tmp/plugins" in loader._plugin_dirs
        loader.add_plugin_dir("/tmp/plugins")  # 重复添加不报错
        assert loader._plugin_dirs.count("/tmp/plugins") == 1


# ══════════════════════════════════════════════════════════════
# 集成测试
# ══════════════════════════════════════════════════════════════


class TestSystemIntegration:
    """完整系统集成测试 / Full system integration tests."""

    def test_create_system(self):
        """创建完整系统 / Create full system."""
        registry, injector, blueprint, plugin_loader = create_system()
        assert registry.count == 0
        assert isinstance(injector, DependencyInjector)
        assert isinstance(blueprint, SystemBlueprint)
        assert isinstance(plugin_loader, PluginLoader)

    def test_register_init_blueprint(self):
        """注册→初始化→蓝图导出完整链路 /
        Full chain: register → init → blueprint."""
        registry, injector, blueprint, _ = create_system()
        registry.register(SimpleComponent("a"))
        registry.register(ComponentWithDeps("b", requires=["a"]))
        registry.register(ComponentWithDeps("c", requires=["b"]))

        results = injector.init_all()
        assert all(r["success"] for r in results)

        data = blueprint.to_dict()
        assert data["total_components"] == 3
        assert len(data["edges"]) == 2

    def test_blueprint_start_order(self):
        """蓝图包含正确启动顺序 / Blueprint contains correct start order."""
        registry, injector, blueprint, _ = create_system()
        registry.register(SimpleComponent("base"))
        registry.register(ComponentWithDeps("mid", requires=["base"]))
        registry.register(ComponentWithDeps("top", requires=["mid"]))

        data = blueprint.to_dict()
        start_order = data["start_order"]
        assert start_order == ["base", "mid", "top"]

    def test_integrity_check(self):
        """模块完整性检查 / Module integrity check."""
        errors = verify_integrity()
        assert len(errors) == 0


# ══════════════════════════════════════════════════════════════
# 向后兼容性 — 原有类型仍然可用
# ══════════════════════════════════════════════════════════════


class TestBackwardCompatibility:
    """向后兼容性测试 / Backward compatibility tests."""

    def test_message_type_enum(self):
        """MessageType 枚举仍然可用 / MessageType enum still available."""
        assert hasattr(MessageType, "TEXT")
        assert hasattr(MessageType, "VOICE")
        assert hasattr(MessageType, "IMAGE")

    def test_agent_capability_enum(self):
        """AgentCapability 枚举仍然可用 / AgentCapability still available."""
        assert hasattr(AgentCapability, "VOICE_INTERACTION")
        assert hasattr(AgentCapability, "FINANCE_PREDICTION")
        assert hasattr(AgentCapability, "MEMORY_MANAGEMENT")

    def test_new_capability(self):
        """新增 ARCHITECTURE 和 PLUGIN 能力 /
        New ARCHITECTURE and PLUGIN capabilities exist."""
        assert hasattr(AgentCapability, "ARCHITECTURE")
        assert hasattr(AgentCapability, "PLUGIN")
