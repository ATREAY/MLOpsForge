#!/usr/bin/env python3
"""Simulates a live feed of Ethereum transactions by streaming real rows from
the same dataset samamba trains on, one at a time, to a Kafka topic —
standing in for whatever real upstream system would actually produce these
events (a chain indexer, a mempool watcher, etc.). Not a synthetic generator:
every row is a real address's real behavioral features from the dataset.

Usage:
    python producer.py --csv ../datasets_registry/ethereum_fraud_detection.csv --limit 30 --rate-per-sec 2
"""

import argparse
import json
import time

import pandas as pd
from kafka import KafkaProducer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="../datasets_registry/ethereum_fraud_detection.csv")
    parser.add_argument("--bootstrap-servers", default="127.0.0.1:9092")
    parser.add_argument("--topic", default="ethereum-transactions")
    parser.add_argument("--rate-per-sec", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--seed", type=int, default=None, help="omit for a different random sample each run")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    sample = df.sample(n=min(args.limit, len(df)), random_state=args.seed).to_dict(orient="records")

    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    delay = 1.0 / args.rate_per_sec
    print(f"[producer] streaming {len(sample)} real transactions to '{args.topic}' at {args.rate_per_sec}/s")

    for i, row in enumerate(sample):
        # FLAG is the ground-truth label — a real upstream feed wouldn't know
        # this yet (that's the entire point of scoring). Kept under a
        # clearly-marked key purely so this demo's own consumer can report
        # whether the live prediction agreed with reality; the model never
        # sees it (inference only reads the feature columns it was trained on).
        true_label = row.pop("FLAG", None)
        row["_true_label_for_demo_only"] = true_label

        producer.send(args.topic, value=row)
        print(f"[producer] {i + 1}/{len(sample)} sent — address={row.get('Address', '?')[:12]}...")
        time.sleep(delay)

    producer.flush()
    print(f"[producer] done — {len(sample)} transactions sent")


if __name__ == "__main__":
    main()
