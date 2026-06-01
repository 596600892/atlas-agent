"""
Atlas WebUI — Flask 后端
==========================
提供 REST API 和静态文件服务，用于 Atlas 的 Web 界面。

启动方式:
    atlas web                  — 默认 8640 端口
    atlas web --port 8080      — 指定端口
    atlas web --host 0.0.0.0   — 开放访问
"""

import json
import logging
import os
import time

from atlas_core.core import Atlas

logger = logging.getLogger("atlas.webui")

# ── 全局 Atlas 实例 ──────────────────────────
_atlas: Atlas = None


def get_atlas() -> Atlas:
    """获取或创建全局 Atlas 实例"""
    global _atlas
    if _atlas is None:
        _atlas = Atlas(
            voice_enabled=False,
            memory_enabled=True,
            data_dir=os.getenv("ATLAS_DATA_DIR", "~/.atlas"),
        )
    return _atlas


# ── Flask App ─────────────────────────────────

def create_app():
    """创建 Flask 应用"""
    try:
        from flask import Flask, jsonify, request, send_from_directory
    except ImportError:
        print("Error: Flask is required for WebUI. Install with: pip install atlas-agent[webui]")
        raise

    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="",
    )

    # ── API 路由 ──────────────────────────

    @app.route("/")
    def index():
        """提供主页面"""
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/status")
    def api_status():
        """系统状态"""
        atlas = get_atlas()
        info = atlas.get_info()
        return jsonify({
            "version": info["version"],
            "agents": info["agents_registered"],
            "queries": info["queries_processed"],
            "voice": info["voice_enabled"],
            "memory": info["memory_enabled"],
            "uptime": info["session_duration_seconds"],
            "status": "ok",
        })

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """处理聊天消息"""
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "Missing 'message' field"}), 400

        query = data["message"].strip()
        if not query:
            return jsonify({"error": "Empty message"}), 400

        atlas = get_atlas()
        result = atlas.process(query)

        return jsonify({
            "response": result["response"],
            "intent": result["intent"],
            "confidence": result["confidence"],
            "matched_agents": [
                {"name": name, "confidence": conf}
                for name, conf in result.get("matched_agents", [])
            ],
            "memories": result.get("memories_recalled", 0),
        })

    @app.route("/api/agents")
    def api_agents():
        """列出所有 Agent"""
        from atlas_core.router_engine import create_router
        router = create_router()
        agents = router.list_all()
        return jsonify([
            {
                "name": a.name,
                "description": a.description,
                "capabilities": [c.value for c in a.capabilities],
                "repo": a.repo_url,
            }
            for a in agents
        ])

    @app.route("/api/routes")
    def api_routes():
        """显示当前路由表"""
        from atlas_core.router_engine import create_router
        router = create_router()
        routes = {}
        for cap_name in dir(type(router).__dict__.get("_PATTERNS", {})) if hasattr(type(router), "_PATTERNS") else []:
            pass
        # 按能力分组
        from atlas_core.router_engine import AgentCapability
        for cap in AgentCapability:
            agents = router.list_by_capability(cap)
            if agents:
                routes[cap.value] = [a.name for a in agents]
        return jsonify(routes)

    return app


# ── 独立启动 ──────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 8640, debug: bool = False):
    """启动 WebUI 服务器"""
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║       Atlas Agent WebUI              ║")
    print(f"  ║                                      ║")
    print(f"  ║  http://{host}:{port}                    ║")
    print(f"  ║                                      ║")
    print(f"  ║  Press Ctrl+C to stop                ║")
    print(f"  ╚══════════════════════════════════════╝\n")

    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Atlas WebUI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8640, help="Bind port")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, debug=args.debug)
