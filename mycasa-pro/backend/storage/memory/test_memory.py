"""
Comprehensive tests for memory system
Actually run these to verify everything works
"""
import asyncio
import json
import shutil
from pathlib import Path
from datetime import datetime, date

# Test with actual implementation
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import manager
import schemas
MemoryManager = manager.MemoryManager
AtomicFact = schemas.AtomicFact
validate_fact = schemas.validate_fact
validate_entity_id = schemas.validate_entity_id
calculate_decay_tier = schemas.calculate_decay_tier


class MemorySystemTester:
    """Test the actual memory system"""

    def __init__(self):
        # Use test directory
        self.test_path = Path("memory_test")
        self.cleanup()
        self.manager = MemoryManager(base_path=str(self.test_path))

    def cleanup(self):
        """Clean up test directory"""
        if self.test_path.exists():
            shutil.rmtree(self.test_path)

    async def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("MEMORY SYSTEM TESTS - VERIFYING ACTUAL IMPLEMENTATION")
        print("=" * 60)

        tests = [
            ("Schema Validation", self.test_schemas),
            ("Entity Creation", self.test_entity_creation),
            ("Fact Writing", self.test_fact_writing),
            ("Fact Superseding", self.test_fact_superseding),
            ("Memory Decay", self.test_memory_decay),
            ("Daily Notes", self.test_daily_notes),
            ("Error Handling", self.test_error_handling),
            ("Atomic Operations", self.test_atomic_operations),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            print(f"\n{'=' * 60}")
            print(f"TEST: {name}")
            print("=" * 60)
            try:
                await test_func()
                print(f"✅ PASSED: {name}")
                passed += 1
            except Exception as e:
                print(f"❌ FAILED: {name}")
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                failed += 1

        print(f"\n{'=' * 60}")
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("=" * 60)

        return failed == 0

    async def test_schemas(self):
        """Test schema validation"""
        print("Testing schema validation...")

        # Test valid fact
        valid_fact = {
            "fact": "Jane is the CTO",
            "category": "relationship",
            "source": "conversation"
        }
        is_valid, error = validate_fact(valid_fact)
        assert is_valid, f"Valid fact rejected: {error}"
        print("  ✓ Valid fact accepted")

        # Test invalid fact - missing fact field
        invalid_fact = {
            "category": "relationship"
        }
        is_valid, error = validate_fact(invalid_fact)
        assert not is_valid, "Invalid fact accepted"
        print("  ✓ Invalid fact rejected correctly")

        # Test invalid category
        invalid_category = {
            "fact": "Some fact",
            "category": "invalid_category"
        }
        is_valid, error = validate_fact(invalid_category)
        assert not is_valid, "Invalid category accepted"
        print("  ✓ Invalid category rejected")

        # Test entity ID validation
        is_valid, error = validate_entity_id("projects/product-launch")
        assert is_valid, f"Valid entity ID rejected: {error}"
        print("  ✓ Valid entity ID accepted")

        is_valid, error = validate_entity_id("invalid")
        assert not is_valid, "Invalid entity ID accepted"
        print("  ✓ Invalid entity ID rejected")

        # Test AtomicFact creation
        fact = AtomicFact(
            fact="Test fact",
            category="milestone",
            source="test"
        )
        assert fact.id.startswith("fact-"), "Fact ID not generated"
        assert fact.status == "active", "Default status not set"
        assert fact.accessCount == 0, "Access count not initialized"
        print("  ✓ AtomicFact object created correctly")

        # Test fact to/from dict
        fact_dict = fact.to_dict()
        assert isinstance(fact_dict, dict), "to_dict() failed"
        fact2 = AtomicFact.from_dict(fact_dict)
        assert fact2.fact == fact.fact, "from_dict() failed"
        print("  ✓ Fact serialization works")

    async def test_entity_creation(self):
        """Test entity creation"""
        print("Testing entity creation...")

        # Create entity
        success, msg = await self.manager.create_entity("projects/test-project")
        assert success, f"Entity creation failed: {msg}"
        print(f"  ✓ Entity created: {msg}")

        # Verify entity exists
        exists = await self.manager.entity_exists("projects/test-project")
        assert exists, "Entity doesn't exist after creation"
        print("  ✓ Entity existence verified")

        # Verify files were created
        entity_path = self.test_path / "global/life/projects/test-project"
        assert entity_path.exists(), "Entity directory not created"
        assert (entity_path / "summary.md").exists(), "summary.md not created"
        assert (entity_path / "items.json").exists(), "items.json not created"
        print("  ✓ Entity files created")

        # Try to create duplicate (should succeed due to idempotency for concurrency)
        success, msg = await self.manager.create_entity("projects/test-project")
        assert success, "Duplicate creation failed (should be idempotent)"
        print("  ✓ Duplicate creation is idempotent")

        # Create entity with nested path
        success, msg = await self.manager.create_entity("areas/people/jane")
        assert success, f"Nested entity creation failed: {msg}"
        print("  ✓ Nested entity created")

    async def test_fact_writing(self):
        """Test fact writing"""
        print("Testing fact writing...")

        # Create entity first
        await self.manager.create_entity("projects/test-facts")

        # Write a fact
        fact = {
            "fact": "Project started in January 2026",
            "category": "milestone",
            "source": "planning-doc"
        }
        success, msg = await self.manager.write_fact("projects/test-facts", fact)
        assert success, f"Fact write failed: {msg}"
        print(f"  ✓ Fact written: {msg}")

        # Verify fact was written
        facts = await self.manager.get_facts("projects/test-facts")
        assert len(facts) == 1, f"Expected 1 fact, got {len(facts)}"
        assert facts[0].fact == fact["fact"], "Fact content doesn't match"
        print("  ✓ Fact retrieved successfully")

        # Write multiple facts
        for i in range(3):
            fact = {
                "fact": f"Milestone {i+1}",
                "category": "milestone",
                "source": "test"
            }
            success, msg = await self.manager.write_fact("projects/test-facts", fact)
            assert success, f"Multiple fact write failed: {msg}"

        facts = await self.manager.get_facts("projects/test-facts")
        assert len(facts) == 4, f"Expected 4 facts, got {len(facts)}"
        print("  ✓ Multiple facts written")

        # Verify atomic write (check JSON is valid)
        items_path = self.test_path / "global/life/projects/test-facts/items.json"
        with open(items_path, 'r') as f:
            data = json.load(f)
            assert isinstance(data, list), "items.json is not a list"
            assert len(data) == 4, f"Expected 4 facts in JSON, got {len(data)}"
        print("  ✓ JSON structure valid")

    async def test_fact_superseding(self):
        """Test fact superseding (no-deletion rule)"""
        print("Testing fact superseding...")

        # Create entity and write initial fact
        await self.manager.create_entity("projects/test-supersede")
        initial_fact = {
            "fact": "Budget is $10,000",
            "category": "status",
            "source": "initial"
        }
        success, msg = await self.manager.write_fact("projects/test-supersede", initial_fact)
        assert success, f"Initial fact write failed: {msg}"

        # Get the fact ID
        facts = await self.manager.get_facts("projects/test-supersede")
        old_fact_id = facts[0].id
        print(f"  ✓ Initial fact written: {old_fact_id}")

        # Supersede with new fact
        new_fact = {
            "fact": "Budget increased to $15,000",
            "category": "status",
            "source": "update"
        }
        success, msg = await self.manager.supersede_fact(
            "projects/test-supersede",
            old_fact_id,
            new_fact
        )
        assert success, f"Supersede failed: {msg}"
        print(f"  ✓ Fact superseded: {msg}")

        # Verify both facts exist
        all_facts = await self.manager.get_facts("projects/test-supersede", status=None)
        assert len(all_facts) >= 2, f"Expected at least 2 facts, got {len(all_facts)}"

        # Verify old fact is marked superseded
        old_fact = [f for f in all_facts if f.id == old_fact_id][0]
        assert old_fact.status == "superseded", "Old fact not marked superseded"
        assert old_fact.supersededBy is not None, "supersededBy not set"
        print("  ✓ Old fact marked superseded")

        # Verify new fact is active
        active_facts = await self.manager.get_facts("projects/test-supersede", status="active")
        assert len(active_facts) == 1, f"Expected 1 active fact, got {len(active_facts)}"
        assert "$15,000" in active_facts[0].fact, "New fact content wrong"
        print("  ✓ New fact is active")

        # Verify no deletion occurred
        items_path = self.test_path / "global/life/projects/test-supersede/items.json"
        with open(items_path, 'r') as f:
            data = json.load(f)
            assert len(data) >= 2, "Old fact was deleted!"
        print("  ✓ No-deletion rule enforced")

    async def test_memory_decay(self):
        """Test memory decay calculation"""
        print("Testing memory decay...")

        # Create fact with recent access
        fact_hot = AtomicFact(
            fact="Recently accessed",
            category="context",
            source="test"
        )
        fact_hot.lastAccessed = datetime.now().isoformat()
        fact_hot.accessCount = 5

        tier = calculate_decay_tier(fact_hot)
        assert tier == "hot", f"Recent fact should be hot, got {tier}"
        print("  ✓ Hot tier calculation correct")

        # Create fact with old access
        from datetime import timedelta
        old_date = datetime.now() - timedelta(days=45)
        fact_cold = AtomicFact(
            fact="Old fact",
            category="context",
            source="test"
        )
        fact_cold.lastAccessed = old_date.isoformat()
        fact_cold.accessCount = 2

        tier = calculate_decay_tier(fact_cold)
        assert tier == "cold", f"Old fact should be cold, got {tier}"
        print("  ✓ Cold tier calculation correct")

        # Create high-frequency fact (resists decay)
        mid_date = datetime.now() - timedelta(days=12)
        fact_frequent = AtomicFact(
            fact="Frequently accessed",
            category="context",
            source="test"
        )
        fact_frequent.lastAccessed = mid_date.isoformat()
        fact_frequent.accessCount = 25  # High frequency

        tier = calculate_decay_tier(fact_frequent)
        assert tier == "hot", f"High-frequency fact should resist decay, got {tier}"
        print("  ✓ Frequency resistance works")

        # Test access tracking
        await self.manager.create_entity("projects/test-decay")
        fact_data = {
            "fact": "Test access tracking",
            "category": "context",
            "source": "test"
        }
        await self.manager.write_fact("projects/test-decay", fact_data)

        facts = await self.manager.get_facts("projects/test-decay")
        fact_id = facts[0].id
        initial_count = facts[0].accessCount

        # Access the fact
        success, msg = await self.manager.access_fact("projects/test-decay", fact_id)
        assert success, f"Access tracking failed: {msg}"

        # Verify access count increased
        facts = await self.manager.get_facts("projects/test-decay")
        new_count = facts[0].accessCount
        assert new_count == initial_count + 1, f"Access count not incremented: {initial_count} -> {new_count}"
        print("  ✓ Access tracking works")

    async def test_daily_notes(self):
        """Test daily notes"""
        print("Testing daily notes...")

        # Write global daily note
        success, msg = await self.manager.append_daily_note(
            "Test global note content",
            agent_id=None,
            note_date=date.today()
        )
        assert success, f"Global daily note failed: {msg}"
        print("  ✓ Global daily note written")

        # Verify file was created
        daily_file = self.test_path / "global/daily" / f"{date.today().isoformat()}.md"
        assert daily_file.exists(), "Daily note file not created"
        print("  ✓ Daily note file exists")

        # Write agent-specific daily note
        success, msg = await self.manager.append_daily_note(
            "Test agent note",
            agent_id="finance",
            note_date=date.today()
        )
        assert success, f"Agent daily note failed: {msg}"
        print("  ✓ Agent daily note written")

        # Verify agent file
        agent_daily_file = self.test_path / "agents/finance/daily" / f"{date.today().isoformat()}.md"
        assert agent_daily_file.exists(), "Agent daily note not created"
        print("  ✓ Agent daily note file exists")

        # Read daily notes
        notes = await self.manager.get_daily_notes(days=1, agent_id=None)
        assert "Test global note content" in notes, "Global note content not retrieved"
        print("  ✓ Daily notes retrieved")

    async def test_error_handling(self):
        """Test error handling and recovery"""
        print("Testing error handling...")

        # Test invalid entity ID
        success, msg = await self.manager.create_entity("invalid")
        assert not success, "Invalid entity ID accepted"
        print("  ✓ Invalid entity ID rejected")

        # Test writing to non-existent entity (should auto-create)
        fact = {
            "fact": "Auto-create test",
            "category": "context",
            "source": "test"
        }
        success, msg = await self.manager.write_fact("projects/auto-created", fact)
        assert success, f"Auto-create failed: {msg}"
        assert await self.manager.entity_exists("projects/auto-created"), "Entity not auto-created"
        print("  ✓ Auto-create on missing entity works")

        # Test invalid fact
        invalid_fact = {
            "category": "milestone"
            # Missing 'fact' field
        }
        success, msg = await self.manager.write_fact("projects/auto-created", invalid_fact)
        assert not success, "Invalid fact accepted"
        print("  ✓ Invalid fact rejected")

        # Test superseding non-existent fact
        success, msg = await self.manager.supersede_fact(
            "projects/auto-created",
            "non-existent-id",
            {"fact": "Test", "category": "context", "source": "test"}
        )
        assert not success, "Superseding non-existent fact succeeded"
        print("  ✓ Superseding non-existent fact rejected")

    async def test_atomic_operations(self):
        """Test atomic write operations"""
        print("Testing atomic operations...")

        await self.manager.create_entity("projects/test-atomic")

        # Write multiple facts rapidly (test concurrency)
        tasks = []
        for i in range(10):
            fact = {
                "fact": f"Concurrent fact {i}",
                "category": "context",
                "source": "concurrent"
            }
            tasks.append(self.manager.write_fact("projects/test-atomic", fact))

        results = await asyncio.gather(*tasks)
        successful = sum(1 for success, _ in results if success)
        assert successful == 10, f"Expected 10 successful writes, got {successful}"
        print("  ✓ Concurrent writes successful")

        # Verify all facts were written
        facts = await self.manager.get_facts("projects/test-atomic")
        assert len(facts) == 10, f"Expected 10 facts, got {len(facts)}"
        print("  ✓ All concurrent facts persisted")

        # Verify JSON is valid (atomic write worked)
        items_path = self.test_path / "global/life/projects/test-atomic/items.json"
        with open(items_path, 'r') as f:
            data = json.load(f)
            assert len(data) == 10, "JSON corrupted"
        print("  ✓ Atomic writes prevented corruption")


async def main():
    """Run all tests"""
    tester = MemorySystemTester()
    try:
        success = await tester.run_all_tests()
        if success:
            print("\n🎉 ALL TESTS PASSED - MEMORY SYSTEM VERIFIED WORKING")
            return 0
        else:
            print("\n❌ SOME TESTS FAILED - SEE ABOVE")
            return 1
    finally:
        # Clean up
        tester.cleanup()
        print("\n✓ Test directory cleaned up")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
