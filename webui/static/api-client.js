/* Atlas — API Client
   轻量 fetch 封装，自动检测 base URL */

const AtlasAPI = (() => {
  const BASE = '';

  async function get(path) {
    const resp = await fetch(BASE + path);
    if (!resp.ok) throw new Error(`GET ${path} → ${resp.status}`);
    return resp.json();
  }

  async function post(path, body) {
    const resp = await fetch(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`POST ${path} → ${resp.status}`);
    return resp.json();
  }

  // SSE streaming via fetch + ReadableStream
  function chatStream(message, sessionId, callbacks) {
    const { onEvent, onError, onDone } = callbacks;
    let buffer = '';

    fetch(BASE + '/api/chat-stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    }).then(async (resp) => {
      if (!resp.ok) {
        onError?.(new Error(`SSE ${resp.status}`));
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete chunk

        let currentEvent = null;
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEvent) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent?.(currentEvent, data);
            } catch (e) {
              // skip malformed JSON
            }
            currentEvent = null;
          }
        }
      }
      onDone?.();
    }).catch(onError);
  }

  return { get, post, chatStream };
})();
