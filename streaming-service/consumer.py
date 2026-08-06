#!/usr/bin/env python3
"""Consumes the simulated transaction feed and scores each one in
near-real-time through the platform's real inference API — the exact same
POST /api/v1/inference/predict/{model_version_id} endpoint the Models page or
a script would call, not a shortcut that bypasses the platform. This proves
the platform's inference path is fast enough for a streaming use case, not
just batch/on-demand calls. Publishes each scored result to an output topic.

Usage:
    python consumer.py --model-version-id <id> --email you@example.com --password ...
"""

import argparse
import json
import time

import httpx
from kafka import KafkaConsumer, KafkaProducer


def authenticate(api_url: str, email: str, password: str) -> str:
    resp = httpx.post(f"{api_url}/auth/login", json={"email": email, "password": password}, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-servers", default="127.0.0.1:9092")
    parser.add_argument("--input-topic", default="ethereum-transactions")
    parser.add_argument("--output-topic", default="ethereum-fraud-scores")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--model-version-id", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--max-messages", type=int, default=None, help="stop after N messages (mainly for testing)")
    args = parser.parse_args()

    token = authenticate(args.api_url, args.email, args.password)

    consumer = KafkaConsumer(
        args.input_topic,
        bootstrap_servers=args.bootstrap_servers,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="fraud-scoring-consumer",
    )
    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print(f"[consumer] listening on '{args.input_topic}', scoring via model version {args.model_version_id}")
    count = 0
    correct = 0
    with httpx.Client(base_url=args.api_url, headers={"Authorization": f"Bearer {token}"}, timeout=15) as client:
        for message in consumer:
            row = dict(message.value)
            true_label = row.pop("_true_label_for_demo_only", None)
            address = row.get("Address", "?")

            start = time.perf_counter()
            resp = client.post(f"/inference/predict/{args.model_version_id}", json={"inputs": row})
            latency_ms = (time.perf_counter() - start) * 1000

            if resp.status_code != 200:
                print(f"[consumer] scoring FAILED for {address}: {resp.status_code} {resp.text[:200]}")
                continue

            prediction = resp.json()["prediction"]
            result = {
                "address": address,
                "fraud_probability": prediction["fraud_probability"],
                "is_fraud": prediction["is_fraud"],
                "true_label_for_demo_only": true_label,
                "scoring_latency_ms": round(latency_ms, 1),
            }
            producer.send(args.output_topic, value=result)

            count += 1
            is_match = true_label is None or bool(true_label) == prediction["is_fraud"]
            correct += int(is_match)
            mark = "✓" if is_match else "✗"
            print(
                f"[consumer] {mark} {address[:12]}... fraud_probability={prediction['fraud_probability']:.3f} "
                f"is_fraud={prediction['is_fraud']} ({latency_ms:.0f}ms)"
            )

            if args.max_messages and count >= args.max_messages:
                break

    producer.flush()
    accuracy = correct / count if count else 0.0
    print(f"[consumer] processed {count} transactions, live accuracy vs ground truth: {accuracy:.1%}")


if __name__ == "__main__":
    main()
