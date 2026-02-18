#!/usr/bin/env python3
"""
SecondBrain CLI
===============

Command-line interface for SecondBrain vault operations.

Usage:
    python scripts/secondbrain_cli.py write --type decision --title "Test" --body "Content"
    python scripts/secondbrain_cli.py search --query "test"
    python scripts/secondbrain_cli.py list [folder]
    python scripts/secondbrain_cli.py show <note_id>
    python scripts/secondbrain_cli.py graph <seed_id> [--depth 2]
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.secondbrain import SecondBrain
from config.settings import get_vault_path
from core.secondbrain.models import NoteType, AgentType, SourceType, Confidence


async def cmd_write(args):
    """Write a new note"""
    sb = SecondBrain(tenant_id=args.tenant, agent=AgentType(args.agent))
    
    note_id = await sb.write_note(
        type=args.type,
        title=args.title,
        body=args.body,
        source=args.source,
        folder=args.folder,
        refs=args.refs.split(",") if args.refs else [],
        entities=args.entities.split(",") if args.entities else [],
        confidence=args.confidence,
        pii=args.pii,
    )
    
    print(f"✓ Created: {note_id}")
    
    # Show file path
    file_path = sb._find_note(note_id)
    if file_path:
        print(f"  Path: {file_path}")


async def cmd_append(args):
    """Append to a note"""
    sb = SecondBrain(tenant_id=args.tenant, agent=AgentType(args.agent))
    
    await sb.append(
        note_id=args.note_id,
        content=args.content,
    )
    
    print(f"✓ Appended to: {args.note_id}")


async def cmd_search(args):
    """Search notes"""
    sb = SecondBrain(tenant_id=args.tenant)
    
    scope = args.scope.split(",") if args.scope else None
    results = await sb.search(
        query=args.query,
        scope=scope,
        limit=args.limit,
    )
    
    if not results:
        print("No results found.")
        return
    
    print(f"Found {len(results)} results:\n")
    for r in results:
        print(f"📄 {r.note_id} (relevance: {r.relevance:.2f})")
        print(f"   Path: {r.file_path}")
        print(f"   {r.snippet[:100]}...")
        print()


async def cmd_list(args):
    """List notes in a folder"""
    vault_path = get_vault_path(args.tenant)
    
    if args.folder:
        folders = [vault_path / args.folder]
    else:
        folders = [f for f in vault_path.iterdir() if f.is_dir() and not f.name.startswith("_")]
    
    total = 0
    for folder in folders:
        if not folder.exists():
            continue
        
        notes = list(folder.glob("*.md"))
        if notes:
            print(f"\n📁 {folder.name}/ ({len(notes)} notes)")
            for note in sorted(notes)[:10]:  # Show first 10
                print(f"   - {note.stem}")
            if len(notes) > 10:
                print(f"   ... and {len(notes) - 10} more")
            total += len(notes)
    
    print(f"\nTotal: {total} notes")


async def cmd_show(args):
    """Show a note"""
    sb = SecondBrain(tenant_id=args.tenant)
    
    file_path = sb._find_note(args.note_id)
    if not file_path:
        print(f"❌ Note not found: {args.note_id}")
        return
    
    content = file_path.read_text()
    print(content)


async def cmd_graph(args):
    """Traverse knowledge graph"""
    sb = SecondBrain(tenant_id=args.tenant)
    
    result = await sb.get_graph(seed_id=args.seed_id, depth=args.depth)
    
    print(f"Graph from {args.seed_id} (depth {args.depth}):\n")
    
    print("Nodes:")
    for node in result.nodes:
        print(f"  [{node.type}] {node.id}: {node.label}")
    
    print("\nEdges:")
    for edge in result.edges:
        print(f"  {edge.from_id} --{edge.relation}--> {edge.to_id}")


async def cmd_seed(args):
    """Seed vault with sample data"""
    sb = SecondBrain(tenant_id=args.tenant, agent=AgentType.MANAGER)
    
    print("Seeding vault with sample data...\n")
    
    # Create some entities
    juan_id = await sb.write_note(
        type=NoteType.ENTITY,
        title="Juan (Contractor)",
        body="""## Contact Info
- Phone: +1 (253) 431-2046
- Service: General Contractor
- Languages: Spanish, English

## Notes
Recommended by neighbor. Good for roofing, fencing, general repairs.
Fair pricing, reliable scheduling.""",
        source=SourceType.USER,
        confidence=Confidence.HIGH,
    )
    print(f"✓ Entity: {juan_id}")
    
    # Create a decision
    decision_id = await sb.write_note(
        type=NoteType.DECISION,
        title="Approve Fence Repair Quote",
        body="""Approved Juan's quote for fence repair.

## Details
- Quote amount: $2,800
- Work scope: Replace damaged sections of backyard fence
- Timeline: 2 weeks

## Rationale
- Competitive pricing (compared 3 quotes)
- Good prior experience with Juan
- Can start within the month""",
        source=SourceType.USER,
        entities=["ent_contractor_juan"],
        confidence=Confidence.HIGH,
    )
    print(f"✓ Decision: {decision_id}")
    
    # Create a maintenance task
    task_id = await sb.write_note(
        type=NoteType.TASK,
        title="Schedule HVAC Filter Replacement",
        body="""## Task
Replace HVAC filters (quarterly maintenance)

## Details
- Filter size: 20x25x1
- Location: Utility closet, main floor
- Last replaced: 2025-10-15

## Action Items
- [ ] Order filters from Amazon
- [ ] Schedule 30 min on weekend""",
        folder="maintenance",
        source=SourceType.SYSTEM,
        confidence=Confidence.MEDIUM,
    )
    print(f"✓ Task: {task_id}")
    
    # Create a finance record
    finance_id = await sb.write_note(
        type=NoteType.EVENT,
        title="Portfolio Rebalance - Q1 2026",
        body="""## Summary
Quarterly portfolio rebalance completed.

## Changes
- Increased NVDA position by 100 shares
- Sold 50 SCHD (took profits)
- Added to OUNZ for gold exposure

## Rationale
AI sector momentum continues. Taking some dividend income off the table.
Gold as hedge against rate uncertainty.""",
        folder="finance",
        source=SourceType.USER,
        confidence=Confidence.HIGH,
    )
    print(f"✓ Finance event: {finance_id}")
    
    # Create a policy note
    policy_id = await sb.write_note(
        type=NoteType.POLICY,
        title="Contractor Approval Policy",
        body="""## Policy: Contractor Work Approval

### Threshold Levels
- Under $500: Auto-approve, notify user
- $500 - $2,500: Require user confirmation
- Over $2,500: Require 2+ quotes, user decision

### Required Info for Quotes
1. Detailed scope of work
2. Timeline estimate
3. Material vs labor breakdown
4. Warranty/guarantee terms

### Preferred Vendors
- General: Juan (+1 253-431-2046)
- Plumbing: TBD
- Electrical: TBD""",
        source=SourceType.USER,
        confidence=Confidence.HIGH,
    )
    print(f"✓ Policy: {policy_id}")
    
    print("\n✓ Vault seeded successfully!")
    print("\nRun 'python scripts/secondbrain_cli.py list' to see all notes.")


def main():
    parser = argparse.ArgumentParser(description="SecondBrain CLI")
    parser.add_argument("--tenant", default="tenkiang_household", help="Tenant ID")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # write command
    write_parser = subparsers.add_parser("write", help="Write a new note")
    write_parser.add_argument("--type", required=True, choices=[t.value for t in NoteType])
    write_parser.add_argument("--title", required=True)
    write_parser.add_argument("--body", required=True)
    write_parser.add_argument("--agent", default="manager", choices=[a.value for a in AgentType])
    write_parser.add_argument("--source", default="api", choices=[s.value for s in SourceType])
    write_parser.add_argument("--folder", default=None)
    write_parser.add_argument("--refs", default=None, help="Comma-separated ref IDs")
    write_parser.add_argument("--entities", default=None, help="Comma-separated entity IDs")
    write_parser.add_argument("--confidence", default="medium", choices=[c.value for c in Confidence])
    write_parser.add_argument("--pii", action="store_true")
    
    # append command
    append_parser = subparsers.add_parser("append", help="Append to a note")
    append_parser.add_argument("note_id")
    append_parser.add_argument("--content", required=True)
    append_parser.add_argument("--agent", default="manager", choices=[a.value for a in AgentType])
    
    # search command
    search_parser = subparsers.add_parser("search", help="Search notes")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--scope", default=None, help="Comma-separated folders")
    search_parser.add_argument("--limit", type=int, default=10)
    
    # list command
    list_parser = subparsers.add_parser("list", help="List notes")
    list_parser.add_argument("folder", nargs="?", default=None)
    
    # show command
    show_parser = subparsers.add_parser("show", help="Show a note")
    show_parser.add_argument("note_id")
    
    # graph command
    graph_parser = subparsers.add_parser("graph", help="Traverse knowledge graph")
    graph_parser.add_argument("seed_id")
    graph_parser.add_argument("--depth", type=int, default=2)
    
    # seed command
    seed_parser = subparsers.add_parser("seed", help="Seed vault with sample data")
    
    args = parser.parse_args()
    
    # Run command
    cmd_map = {
        "write": cmd_write,
        "append": cmd_append,
        "search": cmd_search,
        "list": cmd_list,
        "show": cmd_show,
        "graph": cmd_graph,
        "seed": cmd_seed,
    }
    
    # CLI entry point - safe to use asyncio.run() at top level
    try:
        loop = asyncio.get_running_loop()
        # If we get here, we're already in an async context (shouldn't happen in CLI)
        loop.run_until_complete(cmd_map[args.command](args))
    except RuntimeError:
        # No running loop - this is the expected case for CLI
        asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()
