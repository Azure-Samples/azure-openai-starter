#!/usr/bin/env python3
"""Read Azure's regional model catalog without deploying resources or invoking a model."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

DECISIONS_DOC = "https://learn.microsoft.com/azure/foundry/openai/how-to/decisions"
REGIONS_DOC = (
    "https://learn.microsoft.com/azure/foundry/foundry-models/concepts/"
    "models-sold-directly-by-azure-region-availability"
)


def azure_json(arguments: list[str], subscription: str | None) -> object:
    executable = shutil.which("az")
    if executable is None:
        raise RuntimeError("Azure CLI is required. Install it, then run az login.")
    command = [executable, *arguments, "--output", "json", "--only-show-errors"]
    if subscription:
        command.extend(["--subscription", subscription])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120)
    if result.returncode:
        raise RuntimeError(f"Azure CLI failed ({result.returncode}): {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Azure CLI did not return valid JSON") from error


def catalog_rows(region: str, catalog: object, models: list[str], sku: str) -> list[dict]:
    if isinstance(catalog, dict) and "value" in catalog:
        catalog = catalog["value"]
    if not isinstance(catalog, list):
        raise ValueError("The model catalog must be an array or an object containing a value array")
    rows = []
    for wanted in models:
        versions = []
        for entry in catalog:
            if not isinstance(entry, dict):
                raise ValueError("Every model catalog entry must be an object")
            model = entry.get("model", entry)
            if not isinstance(model, dict) or not isinstance(model.get("name"), str):
                raise ValueError("A model catalog entry is missing its model name")
            if model["name"] != wanted:
                continue
            skus = entry.get("skus", model.get("skus"))
            if skus is not None and not isinstance(skus, list):
                raise ValueError("Model skus must be an array when provided")
            sku_names = []
            for item in skus or []:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                    raise ValueError("Every model SKU must have a name")
                sku_names.append(item["name"])
            versions.append({
                "version": model.get("version"),
                "skus": sku_names,
                "requested_sku_listed": sku in sku_names if skus is not None else None,
            })
        rollout = "not_applicable"
        if wanted == "gpt-6-luna":
            rollout = "excluded_in_public_docs" if region == "eastus2" else "verify_service_support"
        rows.append({
            "region": region,
            "model": wanted,
            "catalog": "listed" if versions else "not_listed",
            "versions": versions,
            "decisions_rollout": rollout,
        })
    return rows


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    regions = parser.add_mutually_exclusive_group()
    regions.add_argument("--region", action="append", help="Azure region name; repeat to compare regions")
    regions.add_argument("--all-regions", action="store_true",
                         help="Query every location visible to the subscription; can take several minutes")
    parser.add_argument("--model", action="append", help="Model name; defaults to Sol and Luna")
    parser.add_argument("--sku", default="GlobalStandard", help="Deployment SKU to look for in the catalog")
    parser.add_argument("--subscription", help="Azure subscription name or ID; otherwise use the active subscription")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument("--catalog-file", type=Path,
                        help="Inspect saved az cognitiveservices model list JSON instead of querying Azure")
    args = parser.parse_args(argv)
    if not args.region and not args.all_regions:
        location = os.getenv("AZURE_LOCATION")
        if not location:
            parser.error("Specify --region, --all-regions, or AZURE_LOCATION")
        args.region = [location]
    if args.catalog_file and (args.all_regions or len(args.region) != 1):
        parser.error("--catalog-file requires exactly one --region")
    for region in args.region or []:
        if not re.fullmatch(r"[a-z0-9]+", region):
            parser.error(f"Use an Azure region name such as swedencentral, not {region!r}")
    args.model = args.model or ["gpt-6.1-sol", "gpt-6-luna"]
    if any(not name.strip() for name in args.model) or not args.sku.strip():
        parser.error("Model and SKU names must not be empty")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_arguments(argv)
    regions = args.region
    if args.all_regions:
        locations = azure_json(["account", "list-locations"], args.subscription)
        if not isinstance(locations, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("name"), str)
            for item in locations
        ):
            raise ValueError("Azure CLI returned an invalid location list")
        regions = [item["name"] for item in locations]
        if not regions:
            raise ValueError("No subscription locations were returned")
    rows = []
    for region in dict.fromkeys(regions):
        if args.catalog_file:
            catalog = json.loads(args.catalog_file.read_text(encoding="utf-8"))
        else:
            catalog = azure_json(["cognitiveservices", "model", "list", "--location", region],
                                 args.subscription)
        rows.extend(catalog_rows(region, catalog, args.model, args.sku))
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": "saved_catalog" if args.catalog_file else "azure_management_plane",
        "requested_sku": args.sku,
        "models": rows,
        "limitations": [
            "Catalog visibility is not a quota, capacity, deployment, or Decisions endpoint guarantee.",
            "An absent SKU list means unknown, not unsupported.",
            "East US 2 is excluded by the Decisions rollout documentation checked 2026-10-23; recheck the source.",
            "Confirm Azure support for JSON, tool history, caching, and Live separately.",
        ],
        "sources": [REGIONS_DOC, DECISIONS_DOC],
    }
    if args.format == "json":
        print(json.dumps(report, indent=2))
        return
    print("REGION          MODEL          CATALOG     VERSION / SKUS                 DECISIONS")
    for row in rows:
        versions = "; ".join(
            f"{item['version'] or 'unknown'} / {','.join(item['skus']) or 'unknown'}"
            for item in row["versions"]
        ) or "-"
        print(f"{row['region']:<15} {row['model']:<14} {row['catalog']:<11} "
              f"{versions:<30} {row['decisions_rollout']}")
    for limitation in report["limitations"]:
        print(f"Note: {limitation}")
    print(f"Sources: {REGIONS_DOC}\n         {DECISIONS_DOC}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"Availability check failed: {error}", file=sys.stderr)
        sys.exit(1)
