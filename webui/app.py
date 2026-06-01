"""
Atlas WebUI — Flask 后端 v2 (SSE 事件流版)
==============================================
BaiLongma 启发式重构 Phase 1:
  - SSE 事件流端点 (POST /api/chat-stream)
  - TTS 音频生成 (POST /api/tts)
  - 记忆图谱 API (GET /api/memories)
  - 对话历史 API (GET /api/conversations)
  - 向后兼容原有 /api/chat 等路由

启动方式:
    atlas web                  — 默认 8645 端口
    atlas web --port 8080      — 指定端口
"""

import json
import logging
import os
import time
import uuid
from io import BytesIO

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context
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


# ── SSE 事件格式 ─────────────────────────────

def sse_event(event_type: str, data: dict) -> str:
    """格式化为 SSE 事件字符串"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── Flask App ─────────────────────────────────

def create_app():
    """创建 Flask 应用"""
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
        static_url_path="",
    )

    # ── 静态页面 ──────────────────────────

    @app.route("/")
    def index():
        """提供主页面"""
        return send_from_directory(app.static_folder, "index.html")

    # ── API: 系统状态 ─────────────────────

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
            "conversations": info["conversation_history"],
            "status": "ok",
        })

    # ── API: 聊天（JSON 同步版，向后兼容） ─

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """处理聊天消息（同步 JSON 响应）"""
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

    # ── API: 流式聊天（SSE 事件流） ───────

    @app.route("/api/chat-stream", methods=["POST"])
    def api_chat_stream():
        """流式聊天 — 返回 SSE 事件流

        前端用 fetch + ReadableStream 消费。
        事件类型: message_received, intent_analyzing, intent_result,
                  memory_recalling, memory_result, stream_start,
                  stream_chunk, stream_end, response, error
        """
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "Missing 'message' field"}), 400

        query = data["message"].strip()
        if not query:
            return jsonify({"error": "Empty message"}), 400

        session_id = data.get("session_id", str(uuid.uuid4())[:8])

        def generate():
            atlas = get_atlas()
            yield sse_event("session_start", {"session_id": session_id})
            for event in atlas.process_stream(query):
                yield sse_event(event["type"], event["data"])

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ── API: 记忆清单（力导向图节点） ─────

    @app.route("/api/memories")
    def api_memories():
        """获取记忆节点列表（供前端力导向图渲染）"""
        atlas = get_atlas()
        nodes = []
        edges = []

        if atlas._memory_enabled and atlas._memory_store:
            try:
                # 尝试获取所有记忆
                all_memories = atlas._memory_store.recall("", limit=100)
                for i, m in enumerate(all_memories):
                    nodes.append({
                        "id": f"mem_{i}",
                        "label": m.get("key", f"memory_{i}")[:20],
                        "content": m.get("content", "")[:80],
                        "type": m.get("type", "fact"),
                        "importance": m.get("importance", 0.5),
                        "group": hash(m.get("type", "fact")) % 4,
                        "active": m.get("importance", 0.5) > 0.3,
                    })
                # 生成随机边
                for i in range(1, len(nodes)):
                    edges.append({
                        "source": i,
                        "target": max(0, i - 1 - (i % 3)),
                        "weight": 0.5,
                    })
            except Exception as e:
                logger.warning("Memory fetch failed: %s", e)

        # Fallback: 如果没有记忆，用 Agent 列表做节点
        if not nodes:
            router = get_atlas().router
            agents = router.list_all()
            for a in agents:
                nodes.append({
                    "id": f"agent_{a.name}",
                    "label": a.name,
                    "content": a.description[:60] if a.description else "",
                    "type": "agent",
                    "importance": 0.7,
                    "group": 0,
                    "active": True,
                })
            for i in range(1, len(nodes)):
                edges.append({
                    "source": i,
                    "target": max(0, i - 1),
                    "weight": 0.3 + (i / len(nodes)) * 0.4,
                })

        return jsonify({"nodes": nodes, "edges": edges})

    # ── API: 对话历史 ─────────────────────

    @app.route("/api/conversations")
    def api_conversations():
        """获取对话历史"""
        atlas = get_atlas()
        return jsonify({
            "conversations": atlas.conversation_history[-50:],
            "total": len(atlas.conversation_history),
        })

    # ── API: Agent 清单 ────────────────────

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

    # ── API: 路由表 ────────────────────────

    @app.route("/api/routes")
    def api_routes():
        """显示当前路由表"""
        from atlas_core.router_engine import AgentCapability
        router = get_atlas().router
        routes = {}
        for cap in AgentCapability:
            agents = router.list_by_capability(cap)
            if agents:
                routes[cap.value] = [a.name for a in agents]
        return jsonify(routes)

    # ── API: TTS 音频生成 ──────────────────

    @app.route("/api/tts", methods=["POST"])
    def api_tts():
        """生成 TTS 音频

        请求: {"text": "要朗读的文本", "voice": "zh-CN"}
        响应: WAV 音频二进制
        """
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "Missing 'text' field"}), 400

        text = data["text"].strip()[:1000]  # 限制长度

        try:
            import requests as http_req
            # 尝试通过 Hermes API 调用 TTS
            resp = http_req.post(
                "http://localhost:8642/v1/audio/speech",
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": data.get("voice", "zh-CN"),
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return Response(
                    resp.content,
                    mimetype="audio/wav",
                    headers={"Content-Type": "audio/wav"},
                )
        except Exception as e:
            logger.warning("TTS API call failed (non-critical): %s", e)

        # Fallback: 返回空音频占位
        return jsonify({"status": "unavailable", "message": "TTS service unavailable, use browser Web Speech API"}), 503

    return app


# ── 独立启动 ──────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 8645, debug: bool = False):
    """启动 WebUI 服务器"""
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║       Atlas Agent WebUI v2           ║")
    print(f"  ║     SSE Streaming · TTS · Memories   ║")
    print(f"  ║                                      ║")
    print(f"  ║  http://{host}:{port}                    ║")
    print(f"  ║                                      ║")
    print(f"  ║  Press Ctrl+C to stop                ║")
    print(f"  ╚══════════════════════════════════════╝\n")

    app = create_app()
    logger.info("Pre-warming Atlas instance...")
    get_atlas()
    logger.info("Atlas ready.")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Atlas WebUI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8640, help="Bind port")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, debug=args.debug)
