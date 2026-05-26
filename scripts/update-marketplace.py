#!/usr/bin/env python3
"""
Add a new plugin entry to .claude-plugin/marketplace.json.
Skips silently if the plugin is already listed.
Usage: update-marketplace.py <marketplace.json> <plugin-name> <description>
"""
import json, sys

marketplace_file = sys.argv[1]
plugin_name      = sys.argv[2]
description      = sys.argv[3] if len(sys.argv) > 3 else ""

with open(marketplace_file, encoding="utf-8") as f:
    data = json.load(f)

if any(p["name"] == plugin_name for p in data["plugins"]):
    print(f"[marketplace] {plugin_name} already listed — skipping")
    sys.exit(0)

data["plugins"].append({
    "name":        plugin_name,
    "source":      f"./plugins/{plugin_name}",
    "description": description,
    "category":    "legal",
    "author":      {"name": "Chaim Marcus", "email": "chaim@marcus-law.co.il"}
})

with open(marketplace_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print(f"[marketplace] Added {plugin_name}")
