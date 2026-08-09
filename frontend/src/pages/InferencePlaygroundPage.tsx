import { useMemo, useState } from "react";

import { ApiError } from "@/api/client";
import { useDataset, useDatasets, useModelVersions, usePlugins, usePredict } from "@/api/hooks";
import { Button, Card, ModelStageBadge, PageHeader } from "@/components/ui";

// Plugins that don't match one of the known shapes below (predict()'s input
// shape isn't exposed as JSON Schema anywhere — see plugins/*/plugin.py
// docstrings) fall back to a raw-JSON textarea rather than guessing wrong.
const DIGIT_LABELS = Array.from({ length: 10 }, (_, i) => String(i));
const CORA_CLASS_LABELS = ["0", "1", "2", "3", "4", "5", "6"];
const GRID = 28;

function extractErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    try {
      const parsed = JSON.parse(error.message) as { detail?: unknown };
      if (typeof parsed.detail === "string") return parsed.detail;
    } catch {
      // body wasn't JSON — fall through to the raw text
    }
    return error.message;
  }
  return error instanceof Error ? error.message : String(error);
}

// Single accent color (cyan-500, #06b6d4) for the "winner" bar, muted slate
// for the rest — magnitude is encoded by width, color only marks the
// predicted class. Validated against this dark surface as an ordinal ramp
// (dataviz skill's validate_palette.js --mode dark --ordinal: all checks pass).
function ProbabilityBars({
  probabilities,
  labels,
  highlightIndex,
}: {
  probabilities: number[];
  labels: string[];
  highlightIndex: number;
}) {
  return (
    <div className="space-y-1.5">
      {probabilities.map((p, i) => (
        <div key={labels[i]} className="flex items-center gap-2">
          <span className="w-6 text-right font-mono text-xs font-medium text-slate-500">{labels[i]}</span>
          <div className="h-3 flex-1 overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full rounded-full ${i === highlightIndex ? "bg-cyan-500" : "bg-slate-600"}`}
              style={{ width: `${Math.max(p * 100, 1.5)}%` }}
            />
          </div>
          <span className="w-12 text-right font-mono text-xs text-slate-400">{(p * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

// Real MNIST strokes are anti-aliased and several pixels wide, not a single
// hard-edged pixel line — painting a soft falloff brush (rather than one
// pixel per mouse position) makes hand-drawn input look much more like what
// the model actually trained on.
const BRUSH = [
  [0, 0, 255],
  [1, 0, 170],
  [-1, 0, 170],
  [0, 1, 170],
  [0, -1, 170],
  [1, 1, 90],
  [1, -1, 90],
  [-1, 1, 90],
  [-1, -1, 90],
] as const;

function paintCell(pixels: number[], index: number, mode: "draw" | "erase"): number[] {
  const next = pixels.slice();
  const row = Math.floor(index / GRID);
  const col = index % GRID;

  if (mode === "erase") {
    for (const [dr, dc] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
      const r = row + dr;
      const c = col + dc;
      if (r >= 0 && r < GRID && c >= 0 && c < GRID) next[r * GRID + c] = 0;
    }
    return next;
  }

  for (const [dr, dc, intensity] of BRUSH) {
    const r = row + dr;
    const c = col + dc;
    if (r >= 0 && r < GRID && c >= 0 && c < GRID) {
      const idx = r * GRID + c;
      next[idx] = Math.max(next[idx], intensity);
    }
  }
  return next;
}

// MNIST digits are centered by center-of-mass within the 28x28 frame; a
// hand-drawn doodle usually isn't. Re-centering before submission (not while
// drawing, so the canvas stays WYSIWYG) closes a real accuracy gap without
// touching what the user sees.
function centerOfMass(pixels: number[]): number[] {
  let total = 0;
  let sumRow = 0;
  let sumCol = 0;
  for (let r = 0; r < GRID; r++) {
    for (let c = 0; c < GRID; c++) {
      const v = pixels[r * GRID + c];
      total += v;
      sumRow += v * r;
      sumCol += v * c;
    }
  }
  if (total === 0) return pixels;

  const shiftRow = Math.round(GRID / 2 - 0.5 - sumRow / total);
  const shiftCol = Math.round(GRID / 2 - 0.5 - sumCol / total);
  if (shiftRow === 0 && shiftCol === 0) return pixels;

  const out = new Array(GRID * GRID).fill(0);
  for (let r = 0; r < GRID; r++) {
    for (let c = 0; c < GRID; c++) {
      const nr = r + shiftRow;
      const nc = c + shiftCol;
      if (nr >= 0 && nr < GRID && nc >= 0 && nc < GRID) {
        out[nr * GRID + nc] = pixels[r * GRID + c];
      }
    }
  }
  return out;
}

function DigitCanvas({ pixels, onChange }: { pixels: number[]; onChange: (pixels: number[]) => void }) {
  const [drawMode, setDrawMode] = useState<"draw" | "erase" | null>(null);

  function paint(index: number, mode: "draw" | "erase") {
    onChange(paintCell(pixels, index, mode));
  }

  return (
    <div>
      {/* Kept as a light drawing surface — like a physical whiteboard/paper —
          even inside the dark chrome around it; the pixel values sent to the
          model are unaffected by this display choice (see the module doc). */}
      <div className="inline-block rounded-md border border-slate-700 bg-slate-950 p-2">
        <div
          className="inline-grid select-none gap-px rounded bg-slate-300 p-px"
          style={{ gridTemplateColumns: `repeat(${GRID}, 12px)` }}
          onMouseLeave={() => setDrawMode(null)}
          onMouseUp={() => setDrawMode(null)}
        >
          {pixels.map((v, i) => (
            <div
              key={i}
              onMouseDown={(e) => {
                const mode = e.shiftKey ? "erase" : "draw";
                setDrawMode(mode);
                paint(i, mode);
              }}
              onMouseEnter={() => drawMode && paint(i, drawMode)}
              style={{ width: 12, height: 12, backgroundColor: `rgb(${255 - v}, ${255 - v}, ${255 - v})` }}
            />
          ))}
        </div>
      </div>
      <div className="mt-2 flex items-center gap-3">
        <Button variant="secondary" onClick={() => onChange(new Array(GRID * GRID).fill(0))}>
          Clear
        </Button>
        <p className="text-xs text-slate-500">Click and drag to draw a digit. Shift-click to erase.</p>
      </div>
    </div>
  );
}

function MnistInputs({ onSubmit, pending }: { onSubmit: (inputs: unknown) => void; pending: boolean }) {
  const [pixels, setPixels] = useState<number[]>(() => new Array(GRID * GRID).fill(0));
  const hasInk = pixels.some((v) => v > 0);

  return (
    <div>
      <DigitCanvas pixels={pixels} onChange={setPixels} />
      <div className="mt-4">
        <Button onClick={() => onSubmit({ pixels: centerOfMass(pixels) })} disabled={!hasInk || pending}>
          {pending ? "Predicting…" : "Predict digit"}
        </Button>
      </div>
    </div>
  );
}

function GcnInputs({ onSubmit, pending }: { onSubmit: (inputs: unknown) => void; pending: boolean }) {
  const { data: datasets } = useDatasets();
  const [datasetId, setDatasetId] = useState("");
  const [datasetVersionId, setDatasetVersionId] = useState("");
  const [nodeIndicesRaw, setNodeIndicesRaw] = useState("0, 1, 2");

  const { data: dataset } = useDataset(datasetId || undefined);
  const version = dataset?.versions.find((v) => v.id === datasetVersionId);

  const nodeIndices = useMemo(
    () =>
      nodeIndicesRaw
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => Number.isInteger(n) && n >= 0),
    [nodeIndicesRaw],
  );

  const canSubmit = !!version && nodeIndices.length > 0;

  return (
    <div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Dataset</label>
          <select
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
            value={datasetId}
            onChange={(e) => {
              setDatasetId(e.target.value);
              setDatasetVersionId("");
            }}
          >
            <option value="">Select…</option>
            {datasets?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        {dataset && (
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Dataset version</label>
            <select
              className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
              value={datasetVersionId}
              onChange={(e) => setDatasetVersionId(e.target.value)}
            >
              <option value="">Select…</option>
              {dataset.versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version}
                </option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Node indices (comma-separated)</label>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
            value={nodeIndicesRaw}
            onChange={(e) => setNodeIndicesRaw(e.target.value)}
            placeholder="0, 1, 2"
          />
        </div>
      </div>

      <div className="mt-4">
        <Button
          onClick={() =>
            version &&
            onSubmit({
              dataset_path: version.storage_uri.replace(/^file:\/\//, ""),
              node_indices: nodeIndices,
            })
          }
          disabled={!canSubmit || pending}
        >
          {pending ? "Predicting…" : "Predict node class"}
        </Button>
      </div>
    </div>
  );
}

function SamambaInputs({ onSubmit, pending }: { onSubmit: (inputs: unknown) => void; pending: boolean }) {
  const [address, setAddress] = useState("");

  return (
    <div>
      <div className="mb-3 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
        Known gap: <code className="font-mono">inference-service</code> can't serve real SAMamba predictions yet
        (its shared venv lacks <code className="font-mono">torch_geometric</code>, and the real Mamba SSM kernels
        need CUDA even at inference time). This will fail with a 502 — see{" "}
        <code className="font-mono">inference-service/README.md</code>. Try it anyway to see the real error.
      </div>
      <label className="mb-1 block text-xs font-medium text-slate-400">Ethereum address</label>
      <input
        className="w-full max-w-md rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 font-mono text-sm text-slate-100"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        placeholder="0x..."
      />
      <p className="mt-1 text-xs text-slate-500">
        Must be an address the model was trained on (transductive node classification) — arbitrary new addresses
        aren't valid inputs.
      </p>
      <div className="mt-4">
        <Button onClick={() => onSubmit({ address })} disabled={!address.trim() || pending}>
          {pending ? "Predicting…" : "Predict"}
        </Button>
      </div>
    </div>
  );
}

function RawJsonInputs({ onSubmit, pending }: { onSubmit: (inputs: unknown) => void; pending: boolean }) {
  const [raw, setRaw] = useState("{}");
  const [parseError, setParseError] = useState<string | null>(null);

  function handleSubmit() {
    try {
      const parsed = JSON.parse(raw);
      setParseError(null);
      onSubmit(parsed);
    } catch {
      setParseError("Not valid JSON.");
    }
  }

  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-400">
        Raw inputs (JSON) — no known input shape for this plugin, see its plugin.py docstring
      </label>
      <textarea
        className="h-28 w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 font-mono text-sm text-slate-100"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
      />
      {parseError && <p className="mt-1 text-xs text-red-400">{parseError}</p>}
      <div className="mt-4">
        <Button onClick={handleSubmit} disabled={pending}>
          {pending ? "Predicting…" : "Predict"}
        </Button>
      </div>
    </div>
  );
}

function PredictionResult({ pluginName, prediction }: { pluginName: string; prediction: unknown }) {
  if (pluginName === "mnist_cnn" && prediction && typeof prediction === "object") {
    const { predicted_digit, probabilities } = prediction as { predicted_digit: number; probabilities: number[] };
    return (
      <div>
        <p className="mb-3 text-sm text-slate-400">
          Predicted digit: <span className="font-mono text-2xl font-semibold text-slate-50">{predicted_digit}</span>
        </p>
        <ProbabilityBars probabilities={probabilities} labels={DIGIT_LABELS} highlightIndex={predicted_digit} />
      </div>
    );
  }

  if (pluginName === "gcn_baseline" && Array.isArray(prediction)) {
    const rows = prediction as { node_index: number; predicted_class: number; probabilities: number[] }[];
    return (
      <div className="space-y-4">
        {rows.map((row) => (
          <div key={row.node_index} className="border-b border-slate-800 pb-4 last:border-0 last:pb-0">
            <p className="mb-2 text-sm text-slate-400">
              Node <span className="font-mono">{row.node_index}</span> — predicted class:{" "}
              <span className="font-mono font-semibold text-slate-50">{row.predicted_class}</span>
            </p>
            <ProbabilityBars
              probabilities={row.probabilities}
              labels={CORA_CLASS_LABELS.slice(0, row.probabilities.length)}
              highlightIndex={row.predicted_class}
            />
          </div>
        ))}
      </div>
    );
  }

  if (pluginName === "samamba" && prediction && typeof prediction === "object") {
    const { address, fraud_probability, is_fraud } = prediction as {
      address: string;
      fraud_probability: number;
      is_fraud: boolean;
    };
    return (
      <div>
        <p className="mb-2 font-mono text-xs text-slate-500">{address}</p>
        <p className="flex items-center gap-2 text-sm text-slate-400">
          Fraud probability:{" "}
          <span className="font-mono text-lg font-semibold text-slate-50">{(fraud_probability * 100).toFixed(1)}%</span>
          <span
            className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
              is_fraud
                ? "border-red-500/30 bg-red-500/10 text-red-300"
                : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
            }`}
          >
            {is_fraud ? "Fraud" : "Not fraud"}
          </span>
        </p>
      </div>
    );
  }

  return (
    <pre className="overflow-x-auto rounded-md border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300">
      {JSON.stringify(prediction, null, 2)}
    </pre>
  );
}

export default function InferencePlaygroundPage() {
  const { data: models } = useModelVersions();
  const { data: plugins } = usePlugins();
  const predict = usePredict();

  const [modelVersionId, setModelVersionId] = useState("");

  const selectedModel = models?.find((m) => m.id === modelVersionId);
  const selectedPlugin = plugins?.find((p) => p.id === selectedModel?.plugin_id);

  function handleSubmit(inputs: unknown) {
    if (!modelVersionId) return;
    predict.mutate({ modelVersionId, inputs });
  }

  function InputForm() {
    if (!selectedPlugin) return null;
    switch (selectedPlugin.name) {
      case "mnist_cnn":
        return <MnistInputs onSubmit={handleSubmit} pending={predict.isPending} />;
      case "gcn_baseline":
        return <GcnInputs onSubmit={handleSubmit} pending={predict.isPending} />;
      case "samamba":
        return <SamambaInputs onSubmit={handleSubmit} pending={predict.isPending} />;
      default:
        return <RawJsonInputs onSubmit={handleSubmit} pending={predict.isPending} />;
    }
  }

  return (
    <div>
      <PageHeader
        title="Inference Playground"
        subtitle="Try a registered model against real inputs, served live by inference-service."
      />

      <Card className="mb-6">
        <label className="mb-1 block text-xs font-medium text-slate-400">Model version</label>
        <select
          className="w-full max-w-md rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100"
          value={modelVersionId}
          onChange={(e) => {
            setModelVersionId(e.target.value);
            predict.reset();
          }}
        >
          <option value="">Select…</option>
          {models?.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} v{m.version} ({m.stage})
            </option>
          ))}
        </select>
        {selectedModel && (
          <div className="mt-2 flex items-center gap-2">
            <ModelStageBadge stage={selectedModel.stage} />
            <span className="font-mono text-xs text-slate-500">plugin: {selectedPlugin?.name ?? "…"}</span>
          </div>
        )}
      </Card>

      {selectedPlugin && (
        <Card className="mb-6">
          <p className="mb-3 text-sm font-medium text-slate-300">Inputs</p>
          <InputForm />
        </Card>
      )}

      {predict.isError && (
        <Card className="mb-6 border-red-500/30 bg-red-500/10">
          <p className="text-sm text-red-300">{extractErrorMessage(predict.error)}</p>
        </Card>
      )}

      {predict.isSuccess && selectedPlugin && (
        <Card>
          <p className="mb-3 text-sm font-medium text-slate-300">Prediction</p>
          <PredictionResult pluginName={selectedPlugin.name} prediction={predict.data.prediction} />
        </Card>
      )}
    </div>
  );
}
