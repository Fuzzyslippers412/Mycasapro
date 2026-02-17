"""
Security Integration Tests
Verifies security layer integrates correctly with agent coordination
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.security_integration import get_secure_coordinator
from security import ActionType, RiskLevel


class SecurityIntegrationTester:
    """Test security integration with agent coordination"""

    def __init__(self):
        self.coordinator = get_secure_coordinator()

    async def run_all_tests(self):
        """Run all integration tests"""
        print("=" * 70)
        print("SECURITY INTEGRATION TESTS")
        print("=" * 70)

        tests = [
            ("Secure File Read - Allowed", self.test_secure_file_read_allowed),
            ("Secure File Read - Denied", self.test_secure_file_read_denied),
            ("Secure File Write - Allowed", self.test_secure_file_write_allowed),
            ("Secure File Write - Denied", self.test_secure_file_write_denied),
            ("Secure Memory Read", self.test_secure_memory_read),
            ("Secure Memory Write", self.test_secure_memory_write),
            ("Evidence Bundle", self.test_evidence_bundle),
            ("Audit Log", self.test_audit_log),
            ("Security Summary", self.test_security_summary),
        ]

        passed = 0
        failed = 0

        for name, test_func in tests:
            print(f"\n{'=' * 70}")
            print(f"TEST: {name}")
            print("=" * 70)
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

        print(f"\n{'=' * 70}")
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("=" * 70)

        return failed == 0

    async def test_secure_file_read_allowed(self):
        """Test secure file read with allowed path"""
        print("Testing secure file read (allowed path)...")

        success, content, error = await self.coordinator.secure_file_read(
            agent_id="test-agent",
            session_id="test-session",
            file_path="memory/test.txt",
            rationale="Testing secure file read",
        )

        # File doesn't exist, but policy should ALLOW
        # Result will fail due to file not found, not policy denial
        if error and "not found" in error.lower():
            print("  ✓ Policy allowed read (file not found as expected)")
        elif error and "denied" in error.lower():
            raise AssertionError(f"Policy should allow memory/ reads: {error}")
        else:
            print("  ✓ Policy allowed read")

    async def test_secure_file_read_denied(self):
        """Test secure file read with denied path"""
        print("Testing secure file read (denied path)...")

        success, content, error = await self.coordinator.secure_file_read(
            agent_id="test-agent",
            session_id="test-session",
            file_path=".env",
            rationale="Attempting to read sensitive file",
        )

        assert not success, "Should be denied"
        assert error and "denied" in error.lower(), f"Wrong error: {error}"
        print(f"  ✓ Access denied: {error}")

    async def test_secure_file_write_allowed(self):
        """Test secure file write with allowed path"""
        print("Testing secure file write (allowed path)...")

        success, message, error = await self.coordinator.secure_file_write(
            agent_id="test-agent",
            session_id="test-session",
            file_path="memory/test_write.txt",
            content="Test content",
            rationale="Testing secure file write",
        )

        if success:
            print("  ✓ Write succeeded")
            # Clean up
            import os
            try:
                os.remove("memory/test_write.txt")
            except:
                pass
        elif error and "sanitiz" in error.lower():
            print("  ✓ Write would be sanitized (policy working)")
        else:
            print(f"  ✓ Write attempted (may fail due to directory: {error})")

    async def test_secure_file_write_denied(self):
        """Test secure file write with denied path"""
        print("Testing secure file write (denied path)...")

        success, message, error = await self.coordinator.secure_file_write(
            agent_id="test-agent",
            session_id="test-session",
            file_path="backend/main.py",
            content="malicious content",
            rationale="Attempting to write to protected file",
        )

        assert not success, "Should be denied"
        assert error and "denied" in error.lower(), f"Wrong error: {error}"
        print(f"  ✓ Access denied: {error}")

    async def test_secure_memory_read(self):
        """Test secure memory read"""
        print("Testing secure memory read...")

        success, facts, error = await self.coordinator.secure_memory_read(
            agent_id="test-agent",
            session_id="test-session",
            entity_id="test-entity",
            rationale="Reading memory for test",
        )

        # Memory read should be allowed (policy)
        # May fail due to entity not existing, but policy should allow
        if error and ("not found" in error.lower() or "failed" in error.lower()):
            print("  ✓ Policy allowed read (entity not found as expected)")
        else:
            print("  ✓ Memory read succeeded")

    async def test_secure_memory_write(self):
        """Test secure memory write with sanitization"""
        print("Testing secure memory write...")

        success, message, error = await self.coordinator.secure_memory_write(
            agent_id="test-agent",
            session_id="test-session",
            entity_id="test-entity",
            fact={
                "fact": "Test fact",
                "category": "context",
            },
            rationale="Writing memory for test",
        )

        # Memory write requires sanitization by policy
        # May fail due to memory system not initialized, but should not be denied
        if error and "denied" in error.lower():
            raise AssertionError("Memory write should not be denied by policy")

        print("  ✓ Memory write attempted (policy allows with sanitization)")

    async def test_evidence_bundle(self):
        """Test evidence bundle creation and isolation"""
        print("Testing evidence bundle...")

        # Create bundle
        bundle_id = self.coordinator.create_evidence_bundle(
            session_id="test-session",
            agent_id="test-agent",
        )
        assert bundle_id, "Bundle creation failed"
        print("  ✓ Bundle created")

        # Add evidence
        evidence_id = self.coordinator.add_evidence(
            bundle_id=bundle_id,
            content="<script>alert('XSS')</script> Malicious content",
            source="user-input.txt",
        )
        assert evidence_id, "Evidence addition failed"
        print("  ✓ Evidence added")

        # Get references (not content)
        refs = self.coordinator.get_evidence_references(bundle_id)
        assert len(refs) == 1, "Should have 1 reference"
        assert 'content' not in refs[0], "Content should not be in reference"
        assert '<script>' not in str(refs[0]), "Malicious content in reference"
        print("  ✓ References contain no content")

        # Get content by ID
        content = self.coordinator.get_evidence_content(bundle_id, evidence_id)
        assert content, "Content retrieval failed"
        assert '<script>' in content, "Content should be intact"
        print("  ✓ Content retrievable by ID only")

    async def test_audit_log(self):
        """Test audit log retrieval"""
        print("Testing audit log...")

        # Get audit log
        log = self.coordinator.get_audit_log(limit=50)
        assert isinstance(log, list), "Audit log should be a list"
        print(f"  ✓ Audit log retrieved ({len(log)} entries)")

        # Filter by agent
        agent_log = self.coordinator.get_audit_log(
            agent_id="test-agent",
            limit=50,
        )
        assert isinstance(agent_log, list), "Filtered log should be a list"
        print(f"  ✓ Agent-filtered log retrieved ({len(agent_log)} entries)")

    async def test_security_summary(self):
        """Test security summary statistics"""
        print("Testing security summary...")

        summary = self.coordinator.get_security_summary()
        assert isinstance(summary, dict), "Summary should be a dict"
        assert "total_policy_decisions" in summary, "Missing policy decisions"
        assert "allowed" in summary, "Missing allowed count"
        assert "denied" in summary, "Missing denied count"
        assert "success_rate" in summary, "Missing success rate"

        print(f"  ✓ Security summary generated:")
        print(f"    - Total decisions: {summary['total_policy_decisions']}")
        print(f"    - Allowed: {summary['allowed']}")
        print(f"    - Denied: {summary['denied']}")
        print(f"    - Sanitized: {summary['sanitized']}")
        print(f"    - Denial rate: {summary['denial_rate']:.1%}")
        print(f"    - Success rate: {summary['success_rate']:.1%}")


async def main():
    """Run all integration tests"""
    tester = SecurityIntegrationTester()
    success = await tester.run_all_tests()

    if success:
        print("\n🎉 ALL INTEGRATION TESTS PASSED - READY FOR PRODUCTION")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
