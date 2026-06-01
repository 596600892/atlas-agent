"""
Atlas WebUI — Flask 后端（atlas_core 集成模块）
=================================================
注入到 atlas_core 包内，支持 `atlas web` 和 `atlas electron` CLI 命令。

静态文件路径: webui/static/ (项目根目录)
"""

import json
import logging
import os
import sys

from atlas_core.core import Atlas

logger = logging.getLogger("atlas.webui")

# ── 路径 ─────────────────────────────────────
# 静态文件位于项目根目录的 webui/static/
_WEBUI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webui")

# ── 全局 Atlas 实例 ──────────────────────────
_atlas: Atlas = None


def get_atlas() -> Atlas:
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
        sys.exit(1)

    static_dir = os.path.join(_WEBUI_DIR, "static")

    app = Flask(
        __name__,
        static_folder=static_dir,
        static_url_path="",
    )

    # ── API 路由 ──────────────────────────

    @app.route("/")
    def index():
        return send_from_directory(static_dir, "index.html")

    @app.route("/api/status")
    def api_status():
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
        from atlas_core.router_engine import AgentCapability, create_router
        router = create_router()
        routes = {}
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
