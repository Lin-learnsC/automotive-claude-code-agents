#!/usr/bin/env python3
"""
Convert Automotive Claude Code Agents to Kimi-compatible formats.

This tool converts:
1. Agent YAML/Markdown → Kimi Skill directories (SKILL.md)
2. Expert Markdown skills → Kimi Skill directories
3. Optional: Bundle everything into a single knowledge-base file for Kimi Web

Usage:
    python tools/convert_to_kimi.py --output-dir ./kimi-output
    python tools/convert_to_kimi.py --bundle-web --output ./kimi-web-kb.md
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def extract_yaml_frontmatter(content: str) -> tuple:
    """Extract YAML frontmatter from markdown content.

    Returns (frontmatter_dict, body) or ({}, content) if no frontmatter.
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body = parts[2].strip()
    fm = {}

    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")

    return fm, body


def parse_agent_yaml(yaml_path: Path) -> dict:
    """Parse a minimal subset of agent YAML into a dict."""
    text = yaml_path.read_text(encoding="utf-8")
    data = {"name": yaml_path.stem, "description": "", "role": "", "category": ""}

    # Extract name
    m = re.search(r'^name:\s*"?([^"\n]+)"?', text, re.MULTILINE)
    if m:
        data["name"] = m.group(1).strip()

    # Extract description
    m = re.search(r'^description:\s*"?([^"\n]+)"?', text, re.MULTILINE)
    if m:
        data["description"] = m.group(1).strip()

    # Extract role / system_prompt (multiline block scalar)
    role_match = re.search(
        r'^(?:role|system_prompt):\s*\|\s*\n((?:[ \t]+.*?\n)+)',
        text,
        re.MULTILINE
    )
    if role_match:
        data["role"] = role_match.group(1).strip()
    else:
        # Try inline
        role_match = re.search(r'^role:\s*"?([^"\n]+)"?', text, re.MULTILINE)
        if role_match:
            data["role"] = role_match.group(1).strip()

    # Category from parent directory
    data["category"] = yaml_path.parent.name
    return data


def convert_agent_yaml_to_kimi_skill(agent_yaml: Path, output_dir: Path) -> Path:
    """Convert an agent YAML file to a Kimi skill directory."""
    data = parse_agent_yaml(agent_yaml)
    skill_name = f"automotive-{data['category']}-{data['name']}"
    skill_dir = output_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    description = data["description"] or f"Automotive {data['category']} specialist agent"
    role = data["role"] or f"Automotive {data['category']} specialist for {data['name']}."

    skill_md = f"""---
name: {skill_name}
description: {description}
---

# {data['name']}

**Domain**: {data['category']}

{role}

## When to Use

Trigger this skill when working on automotive **{data['category']}** topics,
including design, implementation, testing, or validation.

## Standards Reference

- ISO 26262 (Functional Safety)
- AUTOSAR (where applicable)
- ISO 21434 (Cybersecurity)
- MISRA C/C++
"""

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_md, encoding="utf-8")
    return skill_dir


def convert_agent_md_to_kimi_skill(agent_md: Path, output_dir: Path) -> Path:
    """Convert a Claude Code agent Markdown file to Kimi skill."""
    content = agent_md.read_text(encoding="utf-8")
    fm, body = extract_yaml_frontmatter(content)

    category = agent_md.parent.name
    name = fm.get("name", agent_md.stem)
    description = fm.get("description", f"Automotive {category} agent")

    # Remove Claude-specific frontmatter fields that Kimi doesn't need
    skill_name = f"automotive-{category}-{name}"
    skill_dir = output_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = f"""---
name: {skill_name}
description: {description}
---

{body}
"""

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_md, encoding="utf-8")
    return skill_dir


def convert_expert_skill(skill_src_dir: Path, output_dir: Path) -> Optional[Path]:
    """Convert an automotive-{domain} expert skill directory to Kimi skill."""
    category = skill_src_dir.name  # e.g., "automotive-adas"
    skill_name = category if category.startswith("automotive-") else f"automotive-{category}"
    skill_dir = output_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Find all markdown files in the source directory
    md_files = list(skill_src_dir.rglob("*.md"))
    if not md_files:
        return None

    # Build a composite SKILL.md that references all source files
    file_list = "\n".join(f"- `{f.relative_to(skill_src_dir)}`" for f in sorted(md_files))
    total_files = len(list(skill_src_dir.rglob("*")))

    skill_md = f"""---
name: {skill_name}
description: |
  Automotive {category} domain expertise covering standards, best practices,
  and implementation guidance. Contains {len(md_files)} markdown files.
  TRIGGER: When working on automotive {category} topics.
---

# Automotive Skill: {category}

This skill provides expertise in automotive **{category}** domain.

## Source Files

{file_list}

## Usage

Reference the source content for detailed domain knowledge:
```bash
ls {skill_src_dir}
```

## Quick Reference

"""

    # Append the content of all SKILL.md or README.md files
    for src_file in sorted(md_files):
        if src_file.name.lower() in ("skill.md", "readme.md"):
            content = src_file.read_text(encoding="utf-8")
            fm, body = extract_yaml_frontmatter(content)
            skill_md += f"\n---\n\n## {src_file.stem}\n\n{body}\n"

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_md, encoding="utf-8")
    return skill_dir


def build_web_knowledge_base(output_path: Path, include_skills: bool = True) -> None:
    """Bundle all automotive content into a single Markdown file for Kimi Web."""
    lines = [
        "# Automotive AI Knowledge Base",
        "",
        "> This document is a consolidated knowledge base for automotive software development,",
        "> converted from the automotive-claude-code-agents project for use with Kimi.",
        "",
        "---",
        "",
    ]

    # Agents
    agents_dir = PROJECT_ROOT / "agents"
    if agents_dir.exists():
        lines.append("# Section 1: Domain Agents\n")
        for agent_file in sorted(agents_dir.rglob("*.yaml")):
            data = parse_agent_yaml(agent_file)
            lines.append(f"## {data['category']} — {data['name']}\n")
            lines.append(f"**Description**: {data.get('description', 'N/A')}\n")
            if data.get("role"):
                lines.append(data["role"])
            lines.append("")

        for agent_file in sorted(agents_dir.rglob("*.md")):
            content = agent_file.read_text(encoding="utf-8")
            fm, body = extract_yaml_frontmatter(content)
            lines.append(f"## {agent_file.parent.name} — {fm.get('name', agent_file.stem)}\n")
            lines.append(body)
            lines.append("")

    # Skills
    if include_skills:
        skills_dir = PROJECT_ROOT / "skills"
        if skills_dir.exists():
            lines.append("---\n")
            lines.append("# Section 2: Expert Skills\n")
            for skill_dir in sorted(skills_dir.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                    continue
                lines.append(f"## {skill_dir.name}\n")
                for md_file in sorted(skill_dir.rglob("*.md")):
                    content = md_file.read_text(encoding="utf-8")
                    fm, body = extract_yaml_frontmatter(content)
                    lines.append(f"### {md_file.relative_to(skill_dir)}\n")
                    lines.append(body)
                    lines.append("")

    # Knowledge base
    kb_dir = PROJECT_ROOT / "knowledge-base"
    if kb_dir.exists():
        lines.append("---\n")
        lines.append("# Section 3: Knowledge Base\n")
        for md_file in sorted(kb_dir.rglob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            lines.append(f"## {md_file.relative_to(kb_dir)}\n")
            lines.append(content)
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Automotive Claude Code Agents to Kimi format"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./kimi-skills"),
        help="Output directory for Kimi skills (default: ./kimi-skills)"
    )
    parser.add_argument(
        "--bundle-web",
        action="store_true",
        help="Generate a single knowledge-base Markdown for Kimi Web"
    )
    parser.add_argument(
        "--web-output",
        type=Path,
        default=Path("./kimi-web-kb.md"),
        help="Path for web bundle output (default: ./kimi-web-kb.md)"
    )
    parser.add_argument(
        "--agents-only",
        action="store_true",
        help="Convert only agents, skip skills"
    )
    parser.add_argument(
        "--skills-only",
        action="store_true",
        help="Convert only skills, skip agents"
    )

    args = parser.parse_args()

    if args.bundle_web:
        print(f"Building web knowledge base → {args.web_output}")
        build_web_knowledge_base(args.web_output)
        size_kb = args.web_output.stat().st_size / 1024
        print(f"Done. File size: {size_kb:.1f} KB")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    converted = 0

    # Convert agents
    if not args.skills_only:
        agents_dir = PROJECT_ROOT / "agents"
        if agents_dir.exists():
            print("Converting agents...")
            for agent_file in agents_dir.rglob("*.yaml"):
                out = convert_agent_yaml_to_kimi_skill(agent_file, args.output_dir)
                print(f"  + {out.name}")
                converted += 1
            for agent_file in agents_dir.rglob("*.md"):
                out = convert_agent_md_to_kimi_skill(agent_file, args.output_dir)
                print(f"  + {out.name}")
                converted += 1

    # Convert skills
    if not args.agents_only:
        skills_dir = PROJECT_ROOT / "skills"
        if skills_dir.exists():
            print("Converting skills...")
            for skill_src in sorted(skills_dir.iterdir()):
                if not skill_src.is_dir() or skill_src.name.startswith("_"):
                    continue
                out = convert_expert_skill(skill_src, args.output_dir)
                if out:
                    print(f"  + {out.name}")
                    converted += 1

    print(f"\nConverted {converted} items → {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
