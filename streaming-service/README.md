# streaming-service

Near-real-time Ethereum transaction scoring: a Kafka producer simulating a live transaction feed, and a
consumer that scores each one through the platform's real inference API and publishes the result. Proves the
platform's inference path (`inference-service`, fronted by the backend's auth-gated
`POST /inference/predict/{model_version_id}`) is fast enough for a streaming use case, not just batch/on-demand
calls — this doesn't bypass the platform to score faster, it calls the exact same endpoint the Models page or
`scripts/register_dataset.py`-style tooling would.

## Pieces

- **`producer.py`** — streams real rows from the Ethereum fraud dataset to the `ethereum-transactions` Kafka
  topic, one at a time, standing in for whatever real upstream system would actually produce these events (a
  chain indexer, a mempool watcher). Strips the ground-truth `FLAG` label into a clearly-marked
  `_true_label_for_demo_only` key before sending — the model never sees it; it's there purely so this demo's
  own consumer can report whether the live prediction agreed with reality.
- **`consumer.py`** — subscribes to `ethereum-transactions`, calls the real backend inference API per message
  (authenticating the same way `scripts/register_dataset.py` does), and publishes each scored result to
  `ethereum-fraud-scores`.

## Verified against real infrastructure

Downloaded and ran a real standalone Apache Kafka 4.1.2 broker (KRaft mode — no ZooKeeper, that's been removed
as of Kafka 4.x) plus a portable Temurin JDK 21 (Kafka needs a JVM; neither was installed on the dev machine —
same "download a real standalone binary" pattern as MLflow/Prometheus/Grafana earlier in this project).
Streamed 15 real transactions end to end: real Kafka topics, real inference calls through the authenticated
API, real results on the output topic. **93.3% live accuracy against ground truth**, per-transaction scoring
latency 39–163ms (first call slower — cold model load; `inference-service` doesn't cache loaded models yet,
see its README).

## Running it

Needs a running platform (backend + inference-service) and a Kafka broker reachable at `--bootstrap-servers`.

```bash
pip install -e .

# Terminal 1
python consumer.py --model-version-id <id> --email you@example.com --password ...

# Terminal 2
python producer.py --limit 30 --rate-per-sec 2
```

## Status: Docker Compose service not run here

Like the rest of the Docker Compose stack, `infra/docker-compose.yml` gained a `kafka` service (using
`apache/kafka` image, KRaft mode) but it hasn't been brought up through `docker compose up` — no Docker in this
dev environment. Unlike most of the rest of that stack, though, the *mechanism itself* — a real Kafka broker
doing real produce/consume with our actual producer/consumer scripts — has been fully verified, just via a
standalone binary instead of the container image.
