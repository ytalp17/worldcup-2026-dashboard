# Dash WebSocket Callbacks — Reference

> Saved from the official Dash docs (https://dash.plotly.com/websocket-callbacks).
> **New in Dash 4.2.** This is the authoritative reference for our live-data transport.

## Summary

Dash callbacks normally run over HTTP (request → execute → return). **WebSocket callbacks**
use a persistent connection so the server can *push* updates incrementally and read client
state mid-execution.

- **Requires a FastAPI or Quart backend.** Will not work with Flask's dev server.
- Use for: live data streams, progress indicators, adaptive workflows, real-time logs/events.

## Enabling

Globally:

```python
app = Dash(backend="fastapi", websocket_callbacks=True)
```

Per-callback: add `websocket=True` to the specific `@callback`. Callbacks without it use HTTP.

## set_props — streaming updates

Inside a WebSocket callback, `set_props(component_id, {prop: value})` sends updates
immediately instead of waiting for the return value. Multiple updates per execution.

```python
@callback(Output("countdown-display", "children"), Input("start-btn", "n_clicks"),
          prevent_initial_call=True)
async def countdown(n_clicks):
    for i in range(10, 0, -1):
        set_props("countdown-display", {"children": f"Countdown: {i}"})
        await asyncio.sleep(1)
    return "Done!"
```

## get_prop — reading client state mid-run

Access the WebSocket interface via `ctx.websocket`. `await ws.get_prop(id, prop)` reads the
current value of a component property from the browser (avoids declaring it as `State`).

```python
ws = ctx.websocket
name = await ws.get_prop("name-input", "value")
```

## Persistent callbacks — the key pattern for live dashboards

`@callback(persistent=True)`:
- Starts automatically when the client connects; runs the entire session.
- No loading state shown.
- Requires no `Input`/`Output`. Use `set_props` to push, `ws.get_prop` to read.
- Stops on disconnect; `ws.is_shutdown` becomes `True`.

```python
@callback(persistent=True)
async def background_loop():
    ws = ctx.websocket
    while not ws.is_shutdown:
        set_props("live-display", {"children": get_latest_data()})
        await asyncio.sleep(0.5)
```

## Real-time streaming with Patch + get_prop

```python
@callback(Output("status", "children"), Input("connect-btn", "n_clicks"),
          prevent_initial_call=True)
async def stream_prices(n_clicks):
    ws = ctx.websocket
    if ws is None:
        return "No WebSocket"
    set_props("status", {"children": "Connected"})
    try:
        while True:
            for symbol in ["AAPL", "GOOGL", "MSFT"]:
                patched = Patch()
                patched[symbol] = round(100 + random.random() * 50, 2)
                set_props("prices-store", {"data": patched})
            selected = await ws.get_prop("symbol-select", "value")
            if selected:
                prices = await ws.get_prop("prices-store", "data")
                if prices and selected in prices:
                    set_props("live-price", {"children": f"{selected}: ${prices[selected]}"})
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    return "Disconnected"
```

Patterns: handle `asyncio.CancelledError` for clean disconnect; use `Patch()` for incremental
store updates; use `ws.get_prop` to adapt to current UI state.

## External WebSocket integration

A callback can connect to an external WS service (using the `websockets` library) and forward
data via `set_props`. Dash provides no upstream client. (Our upstream — Highlightly — is REST,
not WS, so we poll it inside the persistent loop instead.)

## Migrating from dcc.Interval

| | `dcc.Interval` | Persistent WebSocket callback |
|---|---|---|
| Direction | Client pulls (HTTP each interval) | Server pushes over open connection |
| Trigger | `Input("interval", "n_intervals")` | Starts automatically on page load |
| Outputs | `Output(...)` + `return` | `set_props()` (no `Output` needed) |
| Read UI state | `State(...)` | `await ws.get_prop(...)` mid-loop |
| Frequency | `interval` prop (ms) | `await asyncio.sleep()` |
| Backend | Any (Flask default) | FastAPI or Quart required |
| Slow callbacks | Stalls/queues requests | Next update waits naturally |

`dcc.Interval` is still fine for apps that don't want a FastAPI/Quart backend, or for
infrequent updates (≥30s) where polling overhead is negligible.

## Security

- **Origin validation:** same-origin by default; add `websocket_allowed_origins=[...]` when embedding.
- **Secure transport:** over HTTPS, connections auto-upgrade to `wss://`.
- **XSS:** `set_props` updates are sanitized before rendering.
- **Server-initiated disconnect:** `await ws.close(code=4001, reason="...")`.

## Deployment

```text
# requirements.txt
dash[fastapi]>=4.2
uvicorn[standard]
```

Without `uvicorn[standard]`, pages serve over HTTP but WS connections silently fail
("No supported WebSocket library detected" in logs).

```bash
# Procfile
web: uvicorn app:app.server --host 0.0.0.0 --port $PORT
```

Plotly Cloud configures WebSocket automatically.

## Connection limits & scaling

- Each active WS callback (incl. each persistent one) holds **one thread** for its duration.
- Thread pool = `min(32, cpu_count + 4)` (default `ThreadPoolExecutor`). So concurrent users
  with persistent callbacks is bounded by pool size; extra connections queue.
- ~8–10 MB memory per concurrent persistent callback (dominated by thread stack).
- Scale: multiple workers behind a load balancer; keep loops efficient; prefer per-callback
  `websocket=True` (releases thread on return) over persistent where possible.

## Handling disconnections

- Persistent callbacks: check `ws.is_shutdown` in the loop condition; clean up after the loop.
- Event-triggered callbacks: catch `asyncio.CancelledError`.
- Server side: `await ws.close(code=..., reason=...)`.

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `websocket_callbacks` | `bool` | `False` | Enable WS transport globally. |
| `websocket_allowed_origins` | `list[str]` | `[]` | Additional allowed origins. |
| `websocket_inactivity_timeout` | `int` | `300000` | Idle timeout (ms). |

## API reference

- `ctx.websocket` — the WS interface when running over WebSocket, else `None`.
- `ws.is_shutdown` — `True` when the connection has closed. Check in long loops.
- `ws.close(code=1000, reason=...)` — close from the server side.
- `ws.get_prop(component_id, prop_name, timeout=30.0)` — async read of a client prop.
- `set_props(id, {prop: value})` — push updates (streamed immediately over WS).
