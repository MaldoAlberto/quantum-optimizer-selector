"""Agente independiente que convierte un problema cuántico en código verificado.

No depende de ningún proveedor: habla con cualquier servidor compatible con la API de OpenAI
(/v1/chat/completions). Por defecto usa Ollama en local. Cubre circuitos (Qiskit), mitigación
de errores QEM (Mitiq), corrección de errores QEC (Deltakit + Stim + PyMatching), estimación
de recursos FTQC (Microsoft QDK, Qualtran) y PennyLane / Braket local. El modelo carga la guía
del dominio, escribe código con pruebas, lo ejecuta y corrige hasta que pasa. El último script
que pasa se guarda en out/<slug>.py, y el agente explica qué optimizó y simplificó.

Configuración (variables de entorno):
    QAGENT_BASE_URL  http://localhost:11434/v1   (Ollama; LM Studio: http://localhost:1234/v1)
    QAGENT_MODEL     qwen2.5-coder:7b
    QAGENT_API_KEY   ollama                      (solo hace falta en proveedores remotos)

Uso:
    .venv/bin/python agent.py "Grover que encuentre |101> en 3 qubits"
    .venv/bin/python agent.py --model qwen3:8b "umbral del código de superficie con ruido SD6"
    .venv/bin/python agent.py tareas/mi_tarea.yaml      # tarea estructurada (ver tarea_plantilla.yaml)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("QAGENT_BASE_URL", "http://localhost:11434/v1").rstrip("/")
DEFAULT_MODEL = os.environ.get("QAGENT_MODEL", "qwen2.5-coder:7b")
API_KEY = os.environ.get("QAGENT_API_KEY", "ollama")

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "out"
GUIDES_DIR = ROOT / "guides"
EXAMPLES_DIR = ROOT / "examples"
# Dominio -> ejemplo verificado que se adjunta a su guía.
GUIDE_EXAMPLES = {
    "circuits": None,
    "qem": "qem_mitiq_zne.py",
    "qec": "qec_deltakit_surface_code.py",
    "ftqc": "ftqc_qdk_estimate.py",
    "multiframework": "pennylane_braket_bell.py",
    "optimization": None,  # se carga desde la skill, ver load_guide
}
OPT_SKILL = ROOT / "skills" / "quantum-circuit-optimizer"
PYTHON = sys.executable  # el .venv que tiene las librerías cuánticas
PASS_MARK = "ALL TESTS PASSED"
TOOL_TIMEOUT_S = 120
HTTP_TIMEOUT_S = 600  # los modelos locales pueden tardar en responder
MAX_TOOL_OUTPUT = 4000  # recorta la salida para no llenar el contexto del modelo
MAX_FAILED_RUNS = 4

SYSTEM = f"""You are a quantum computing engineer and teacher. You turn a request (free text or a
structured task spec) into correct, verified code: circuits and algorithms, error mitigation (QEM),
error correction (QEC), fault-tolerant resource estimation (FTQC), circuit optimization, or PennyLane / Amazon Braket code.

Installed in the execution environment: qiskit, qiskit_aer, mitiq, deltakit, stim, pymatching,
ldpc, qsharp, qualtran, cirq, pennylane, braket (LocalSimulator only), pytket, pyzx, numpy, scipy.

Workflow:
1. Call load_guide for each domain the task touches (circuits, qem, qec, ftqc, multiframework,
   optimization)
   before writing code. Each guide has the verification rule for its domain, known pitfalls of
   the installed versions, and a script that is known to run. Start from that script.
2. In 2-4 sentences, state the method and which observable facts prove it correct. The tests
   must check the task's specification against an independent reference, never just re-derive
   what the code built.
3. Call run_python with ONE complete script that does the work, checks it with plain assert
   statements with explicit tolerances and fixed seeds, prints the metrics the guide asks for,
   and prints exactly "{PASS_MARK}" as its last line only if every assert passed.
   No network, no files, no cloud clients.
4. If the run fails, read the error, fix the script and call run_python again with the full
   corrected script. Stop after {MAX_FAILED_RUNS} failed runs and explain what blocks you.
5. When a run prints "{PASS_MARK}", reply in the user's language with: the method, what the tests
   verified, the key metrics, and a short section "Optimización y simplificación" that explains
   which choices reduced cost (gates, depth, qubits, shots, T count, decoder time) or code size,
   and what the user could try next. Do not paste the code again; it is saved automatically.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "load_guide",
            "description": "Load the guide for one domain: verification rule, pitfalls and a verified example script.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "enum": list(GUIDE_EXAMPLES)},
                },
                "required": ["domain"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": (
                "Run a complete Python script locally with the quantum libraries installed and "
                f'return its output. The script must print "{PASS_MARK}" as its last line when '
                "every assert succeeds."
            ),
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Full Python script."}},
                "required": ["code"],
            },
        },
    },
]

_state = {"last_passing_code": None, "runs": 0, "failed_runs": 0}


def load_guide(domain: str) -> str:
    if domain not in GUIDE_EXAMPLES:
        return f"Unknown domain {domain!r}. Use one of: {', '.join(GUIDE_EXAMPLES)}."
    print(f"  · load_guide: {domain}")
    if domain == "optimization":  # la misma skill que usa Claude Code, sin copiarla
        text = (OPT_SKILL / "SKILL.md").read_text() + "\n" + (OPT_SKILL / "references" / "tools.md").read_text()
        return text + "\n```python\n" + (OPT_SKILL / "scripts" / "optimize.py").read_text() + "```\n"
    text = (GUIDES_DIR / f"{domain}.md").read_text()
    if example := GUIDE_EXAMPLES[domain]:
        text += "\n```python\n" + (EXAMPLES_DIR / example).read_text() + "```\n"
    return text


def run_python(code: str) -> str:
    _state["runs"] += 1
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "candidate.py"
        script.write_text(code)
        try:
            proc = subprocess.run(
                [PYTHON, "-I", str(script)],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=TOOL_TIMEOUT_S,
                env={"PATH": "/usr/bin:/bin", "HOME": tmp},
            )
        except subprocess.TimeoutExpired:
            _state["failed_runs"] += 1
            return f"exit_code: timeout after {TOOL_TIMEOUT_S}s. Reduce qubits or shots."

    passed = proc.returncode == 0 and proc.stdout.strip().endswith(PASS_MARK)
    if passed:
        _state["last_passing_code"] = code
    else:
        _state["failed_runs"] += 1
    output = (proc.stdout + ("\n[stderr]\n" + proc.stderr if proc.stderr else ""))[-MAX_TOOL_OUTPUT:]
    print(f"  · run_python #{_state['runs']}: {'PASSED' if passed else f'failed (exit {proc.returncode})'}")
    return f"exit_code: {proc.returncode}\npassed: {passed}\n{output}"


def call_tool(name: str, raw_args: str) -> str:
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
    except json.JSONDecodeError as e:
        return f"Invalid JSON arguments for {name}: {e}. Call the tool again with valid JSON."
    if name == "load_guide":
        return load_guide(str(args.get("domain", "")))
    if name == "run_python":
        return run_python(str(args.get("code", "")))
    return f"Unknown tool {name!r}. Available: load_guide, run_python."


def chat(model: str, messages: list) -> dict:
    """Una llamada a /chat/completions de cualquier servidor compatible con OpenAI."""
    body = json.dumps({"model": model, "messages": messages, "tools": TOOLS, "temperature": 0.2}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Error {e.code} de {BASE_URL}: {e.read().decode()[:500]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"No se pudo conectar a {BASE_URL} ({e.reason}). ¿Está corriendo `ollama serve`?")


CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def fallback_code(text: str) -> str | None:
    """Los modelos locales pequeños a veces escriben el script en vez de llamar a run_python."""
    blocks = [b for b in CODE_BLOCK.findall(text or "") if PASS_MARK in b]
    return blocks[-1] if blocks else None


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:50] or "algoritmo"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prompt", help="el problema en lenguaje natural, o la ruta a un archivo de tarea (.yaml/.md)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"modelo del servidor (por defecto {DEFAULT_MODEL})")
    parser.add_argument("--max-iterations", type=int, default=12, help="tope de turnos del agente")
    args = parser.parse_args()
    task_file = Path(args.prompt)
    task = task_file.read_text() if task_file.is_file() else args.prompt
    name = task_file.stem if task_file.is_file() else args.prompt

    print(f"Modelo: {args.model} @ {BASE_URL}")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    final_text = None

    for _ in range(args.max_iterations):
        msg = chat(args.model, messages)["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})

        if tool_calls:
            for tc in tool_calls:
                fn = tc["function"]
                result = call_tool(fn["name"], fn.get("arguments", "{}"))
                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": result})
        elif (code := fallback_code(msg.get("content"))) and _state["last_passing_code"] is None:
            print("  · el modelo no llamó a run_python; ejecuto su bloque de código")
            messages.append({"role": "user", "content": "Ran your code block:\n" + run_python(code)})
        else:
            final_text = msg.get("content") or ""
            break

        if _state["failed_runs"] >= MAX_FAILED_RUNS and _state["last_passing_code"] is None:
            messages.append({"role": "user", "content": "Too many failed runs. Explain what blocks you."})
    else:
        print("Se alcanzó el tope de turnos.")

    if final_text:
        print("\n" + final_text)
    print(f"\n{_state['runs']} ejecuciones, {_state['failed_runs']} fallidas")

    if _state["last_passing_code"] is None:
        print("Ningún script pasó las pruebas; no se guardó código.")
        return 1
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{slugify(name)}.py"
    path.write_text(_state["last_passing_code"])
    print(f"Código verificado: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
