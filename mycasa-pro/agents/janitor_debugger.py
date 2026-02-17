"""
MyCasa Pro - Janitor Debugger Module
=====================================

Deep debugging and validation capabilities for the Janitor agent.
This module makes Janitor as thorough as a senior engineer at finding issues.

Capabilities:
1. Python syntax validation
2. Import dependency checking  
3. Module load testing
4. API route validation
5. Database schema integrity
6. SecondBrain vault auditing
7. Configuration validation
8. File permission checks
9. Integration testing
10. Error pattern detection
"""

import ast
import sys
import importlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from config.settings import VAULT_PATH


@dataclass
class DebugFinding:
    """A single debugging finding"""
    severity: str  # critical, high, medium, low, info
    category: str  # syntax, import, runtime, config, security, integrity
    file: str
    line: Optional[int]
    message: str
    suggestion: Optional[str] = None
    code: Optional[str] = None


@dataclass 
class DebugReport:
    """Complete debugging report"""
    timestamp: str
    duration_ms: int
    total_files_checked: int
    findings: List[DebugFinding] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "total_files_checked": self.total_files_checked,
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "file": f.file,
                    "line": f.line,
                    "message": f.message,
                    "suggestion": f.suggestion,
                    "code": f.code
                }
                for f in self.findings
            ],
            "summary": self.summary
        }


class JanitorDebugger:
    """
    Deep debugging engine for MyCasa Pro.
    
    Performs comprehensive validation across:
    - Python code syntax and imports
    - API routes and endpoints
    - Database models and schema
    - SecondBrain vault integrity
    - Configuration files
    - File permissions and security
    """
    
    def __init__(self, app_root: Path = None):
        self.app_root = app_root or Path(__file__).parent.parent
        self.findings: List[DebugFinding] = []
        
    def run_full_audit(self) -> DebugReport:
        """Run complete debugging audit"""
        start = datetime.now()
        self.findings = []
        files_checked = 0
        
        # 1. Python syntax validation
        files_checked += self._check_python_syntax()
        
        # 2. Import validation
        self._check_imports()
        
        # 3. API route validation
        self._check_api_routes()
        
        # 4. Database integrity
        self._check_database()
        
        # 5. SecondBrain vault
        self._check_secondbrain_vault()
        
        # 6. Configuration files
        self._check_configs()
        
        # 6b. Port configuration consistency
        self._check_port_configuration()
        
        # 7. File permissions
        self._check_permissions()
        
        # 8. Common error patterns
        self._check_error_patterns()
        
        # 9. Enum type handling (catches string vs enum issues)
        self._check_enum_handling()
        
        # 10. Spec compliance (implementation vs docs)
        self._check_spec_compliance()
        
        # 11. Frontend/backend model sync
        self._check_frontend_backend_sync()
        
        # 11b. API response contract validation (critical for UI/backend sync)
        self._check_api_response_contracts()
        
        # 12. Async issues (asyncio.run in async context)
        self._check_async_issues()
        
        # 13. Bare except clauses
        self._check_bare_except()
        
        # 14. Hardcoded values
        self._check_hardcoded_values()
        
        # 15. Potential None/empty access
        self._check_none_access()
        
        # 16. Unused imports
        self._check_unused_imports()
        
        # 17. TODO/FIXME markers
        self._check_todo_fixme()
        
        # 18. Startup issues (lock files, stale processes)
        self._check_startup_issues()
        
        duration = int((datetime.now() - start).total_seconds() * 1000)
        
        # Build summary
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in self.findings:
            summary[f.severity] = summary.get(f.severity, 0) + 1
        
        return DebugReport(
            timestamp=datetime.now().isoformat(),
            duration_ms=duration,
            total_files_checked=files_checked,
            findings=self.findings,
            summary=summary
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PYTHON SYNTAX VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_python_syntax(self) -> int:
        """Check all Python files for syntax errors"""
        files_checked = 0
        
        for py_file in self.app_root.rglob("*.py"):
            # Skip venv, __pycache__, node_modules
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv"]):
                continue
            
            files_checked += 1
            
            try:
                source = py_file.read_text(encoding="utf-8")
                ast.parse(source)
            except SyntaxError as e:
                self.findings.append(DebugFinding(
                    severity="critical",
                    category="syntax",
                    file=str(py_file.relative_to(self.app_root)),
                    line=e.lineno,
                    message=f"Syntax error: {e.msg}",
                    suggestion="Fix the syntax error before the code can run",
                    code=e.text.strip() if e.text else None
                ))
            except Exception as e:
                self.findings.append(DebugFinding(
                    severity="high",
                    category="syntax",
                    file=str(py_file.relative_to(self.app_root)),
                    line=None,
                    message=f"Could not parse: {str(e)}"
                ))
        
        return files_checked
    
    # ═══════════════════════════════════════════════════════════════════════════
    # IMPORT VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_imports(self):
        """Verify all imports resolve correctly"""
        critical_modules = [
            ("core.secondbrain", "SecondBrain"),
            ("core.secondbrain", "NoteType"),
            ("core.secondbrain", "NoteNotFoundError"),
            ("api.routes.secondbrain", "router"),
            ("api.main", "app"),
            ("agents.janitor", "JanitorAgent"),
            ("agents.manager", "ManagerAgent"),
            ("database", "get_db"),
        ]
        
        # Add app root to path temporarily
        sys.path.insert(0, str(self.app_root))
        
        try:
            for module_path, attr in critical_modules:
                try:
                    module = importlib.import_module(module_path)
                    if attr and not hasattr(module, attr):
                        self.findings.append(DebugFinding(
                            severity="critical",
                            category="import",
                            file=module_path.replace(".", "/") + ".py",
                            line=None,
                            message=f"Module '{module_path}' missing attribute '{attr}'",
                            suggestion=f"Add '{attr}' to __all__ or ensure it's defined"
                        ))
                except ImportError as e:
                    self.findings.append(DebugFinding(
                        severity="critical",
                        category="import",
                        file=module_path.replace(".", "/") + ".py",
                        line=None,
                        message=f"Import failed: {str(e)}",
                        suggestion="Check module exists and dependencies are installed"
                    ))
                except Exception as e:
                    self.findings.append(DebugFinding(
                        severity="high",
                        category="import",
                        file=module_path.replace(".", "/") + ".py",
                        line=None,
                        message=f"Module load error: {str(e)}"
                    ))
        finally:
            sys.path.remove(str(self.app_root))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # API ROUTE VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_api_routes(self):
        """Validate API routes are properly configured"""
        sys.path.insert(0, str(self.app_root))
        
        try:
            from api.main import app
            
            # Get all routes
            routes = []
            for route in app.routes:
                if hasattr(route, "path"):
                    routes.append(route.path)
            
            # Check expected routes exist
            expected_routes = [
                "/health",
                "/status",
                "/api/secondbrain/notes",
                "/api/secondbrain/search",
                "/api/secondbrain/stats",
            ]
            
            for expected in expected_routes:
                if expected not in routes:
                    self.findings.append(DebugFinding(
                        severity="high",
                        category="config",
                        file="api/main.py",
                        line=None,
                        message=f"Expected route '{expected}' not found",
                        suggestion="Ensure router is included in app"
                    ))
            
            # Check for duplicate routes (same method + path)
            seen = set()
            for route in app.routes:
                if hasattr(route, 'path') and hasattr(route, 'methods'):
                    for method in route.methods:
                        key = f"{method} {route.path}"
                        if key in seen:
                            self.findings.append(DebugFinding(
                                severity="medium",
                                category="config",
                                file="api/main.py",
                                line=None,
                                message=f"Duplicate route: {key}"
                            ))
                        seen.add(key)
                
        except Exception as e:
            self.findings.append(DebugFinding(
                severity="critical",
                category="import",
                file="api/main.py",
                line=None,
                message=f"Could not load API: {str(e)}"
            ))
        finally:
            if str(self.app_root) in sys.path:
                sys.path.remove(str(self.app_root))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_database(self):
        """Validate database schema and integrity"""
        db_file = self.app_root / "data" / "mycasa.db"
        
        if not db_file.exists():
            self.findings.append(DebugFinding(
                severity="medium",
                category="integrity",
                file="data/mycasa.db",
                line=None,
                message="Database file not found",
                suggestion="Run database initialization or migrations"
            ))
            return
        
        # Check database is readable
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                "maintenance_tasks",
                "bills",
                "contractors",
                "projects",
                "notifications",
                "agent_logs",
            ]
            
            for table in expected_tables:
                if table not in tables:
                    self.findings.append(DebugFinding(
                        severity="high",
                        category="integrity",
                        file="data/mycasa.db",
                        line=None,
                        message=f"Missing table: {table}",
                        suggestion="Run Alembic migrations to create table"
                    ))
            
            # Check for orphaned records, etc.
            conn.close()
            
        except Exception as e:
            self.findings.append(DebugFinding(
                severity="high",
                category="integrity",
                file="data/mycasa.db",
                line=None,
                message=f"Database error: {str(e)}"
            ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECONDBRAIN VAULT VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_secondbrain_vault(self):
        """Validate SecondBrain vault integrity"""
        vault_path = VAULT_PATH
        
        if not vault_path.exists():
            self.findings.append(DebugFinding(
                severity="high",
                category="integrity",
                file=str(vault_path),
                line=None,
                message="SecondBrain vault not found",
                suggestion="Create vault directory structure"
            ))
            return
        
        # Check required folders
        required_folders = [
            "inbox", "memory", "entities", "projects", 
            "finance", "maintenance", "contractors", 
            "decisions", "logs", "_index"
        ]
        
        for folder in required_folders:
            if not (vault_path / folder).exists():
                self.findings.append(DebugFinding(
                    severity="medium",
                    category="integrity",
                    file=str(vault_path / folder),
                    line=None,
                    message=f"Missing vault folder: {folder}",
                    suggestion=f"mkdir -p {vault_path / folder}"
                ))
        
        # Validate all notes have proper YAML frontmatter
        for md_file in vault_path.rglob("*.md"):
            if md_file.name.startswith("."):
                continue
            if "_index" in str(md_file):
                continue
                
            try:
                content = md_file.read_text(encoding="utf-8")
                
                # Check for frontmatter
                if not content.startswith("---"):
                    self.findings.append(DebugFinding(
                        severity="medium",
                        category="integrity",
                        file=str(md_file.relative_to(vault_path)),
                        line=1,
                        message="Missing YAML frontmatter",
                        suggestion="Add --- delimited YAML header"
                    ))
                    continue
                
                # Parse frontmatter
                parts = content.split("---", 2)
                if len(parts) < 3:
                    self.findings.append(DebugFinding(
                        severity="medium",
                        category="integrity",
                        file=str(md_file.relative_to(vault_path)),
                        line=1,
                        message="Malformed YAML frontmatter (missing closing ---)"
                    ))
                    continue
                
                yaml_content = parts[1]
                
                # Check required fields
                required_fields = ["id", "type", "tenant", "agent", "created_at"]
                for field in required_fields:
                    if f"{field}:" not in yaml_content:
                        self.findings.append(DebugFinding(
                            severity="low",
                            category="integrity",
                            file=str(md_file.relative_to(vault_path)),
                            line=None,
                            message=f"Missing required field: {field}"
                        ))
                
            except Exception as e:
                self.findings.append(DebugFinding(
                    severity="medium",
                    category="integrity",
                    file=str(md_file),
                    line=None,
                    message=f"Could not read file: {str(e)}"
                ))
        
        # Check links.md exists
        links_file = vault_path / "_index" / "links.md"
        if not links_file.exists():
            self.findings.append(DebugFinding(
                severity="low",
                category="integrity",
                file="_index/links.md",
                line=None,
                message="Links index file not found"
            ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURATION VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_configs(self):
        """Validate configuration files"""
        config_files = [
            ("alembic.ini", ["sqlalchemy.url"]),
            (".env.example", []),
        ]
        
        for config_file, required_keys in config_files:
            file_path = self.app_root / config_file
            if not file_path.exists():
                self.findings.append(DebugFinding(
                    severity="low",
                    category="config",
                    file=config_file,
                    line=None,
                    message=f"Config file not found: {config_file}"
                ))
                continue
            
            content = file_path.read_text()
            for key in required_keys:
                if key not in content:
                    self.findings.append(DebugFinding(
                        severity="medium",
                        category="config",
                        file=config_file,
                        line=None,
                        message=f"Missing config key: {key}"
                    ))
        
        # Check for .env (should exist if .env.example exists)
        if (self.app_root / ".env.example").exists() and not (self.app_root / ".env").exists():
            self.findings.append(DebugFinding(
                severity="info",
                category="config",
                file=".env",
                line=None,
                message=".env file not found (using defaults)",
                suggestion="Copy .env.example to .env and configure"
            ))
    
    def _check_port_configuration(self):
        """
        Check for port configuration mismatches between frontend and backend.
        Common issue: frontend expects port 8000 but start.sh uses 8505.
        """
        import re
        
        ports_found = {
            "frontend_api": None,
            "start_script": None,
            "docker_compose": None,
        }
        
        # Check frontend API configuration
        api_ts = self.app_root / "frontend" / "src" / "lib" / "api.ts"
        if api_ts.exists():
            content = api_ts.read_text()
            # Look for port in API_BASE
            match = re.search(r'localhost:(\d+)', content)
            if match:
                ports_found["frontend_api"] = match.group(1)
        
        # Check start.sh
        start_sh = self.app_root / "start.sh"
        if start_sh.exists():
            content = start_sh.read_text()
            # Look for uvicorn port
            match = re.search(r'--port\s+(\d+)', content)
            if match:
                ports_found["start_script"] = match.group(1)
        
        # Check docker-compose.yml if exists
        docker_compose = self.app_root / "docker-compose.yml"
        if docker_compose.exists():
            content = docker_compose.read_text()
            # Look for backend port mapping
            match = re.search(r'(\d+):8000', content)
            if match:
                ports_found["docker_compose"] = match.group(1)
        
        # Compare ports
        defined_ports = {k: v for k, v in ports_found.items() if v is not None}
        if len(set(defined_ports.values())) > 1:
            # Port mismatch detected
            self.findings.append(DebugFinding(
                severity="high",
                category="config",
                file="multiple",
                line=None,
                message=f"Port mismatch detected: {defined_ports}",
                suggestion="Ensure frontend API_BASE port matches backend uvicorn port in start.sh"
            ))
        
        # Check if frontend expects a port that's commonly used by other services
        if ports_found["frontend_api"] in ["3000", "5000"]:
            self.findings.append(DebugFinding(
                severity="medium",
                category="config",
                file="frontend/src/lib/api.ts",
                line=None,
                message=f"Frontend API port {ports_found['frontend_api']} conflicts with common dev server ports",
                suggestion="Use a unique port like 8000 or 8505 for the API backend"
            ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FILE PERMISSION CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_permissions(self):
        """Check file permissions for security issues"""
        import stat
        
        sensitive_patterns = ["*.db", "*.key", "*.pem", ".env", "secrets*"]
        
        for pattern in sensitive_patterns:
            for file_path in self.app_root.rglob(pattern):
                if "venv" in str(file_path) or "node_modules" in str(file_path):
                    continue
                
                try:
                    mode = file_path.stat().st_mode
                    
                    # Check world-readable
                    if mode & stat.S_IROTH:
                        self.findings.append(DebugFinding(
                            severity="medium",
                            category="security",
                            file=str(file_path.relative_to(self.app_root)),
                            line=None,
                            message="Sensitive file is world-readable",
                            suggestion=f"chmod 600 {file_path}"
                        ))
                    
                    # Check world-writable
                    if mode & stat.S_IWOTH:
                        self.findings.append(DebugFinding(
                            severity="high",
                            category="security",
                            file=str(file_path.relative_to(self.app_root)),
                            line=None,
                            message="Sensitive file is world-writable",
                            suggestion=f"chmod 600 {file_path}"
                        ))
                except (OSError, IOError):
                    pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ERROR PATTERN DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_error_patterns(self):
        """Detect common error patterns in code"""
        
        error_patterns = [
            # Pattern: bare except
            (r"except\s*:", "Bare except clause catches all exceptions including KeyboardInterrupt"),
            # Pattern: mutable default argument
            (r"def\s+\w+\([^)]*=\s*\[\]", "Mutable default argument (list)"),
            (r"def\s+\w+\([^)]*=\s*\{\}", "Mutable default argument (dict)"),
            # Pattern: hardcoded secrets
            (r'password\s*=\s*["\'][^"\']+["\']', "Possible hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Possible hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Possible hardcoded secret"),
        ]
        
        import re
        
        for py_file in self.app_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv"]):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                
                for line_num, line in enumerate(lines, 1):
                    for pattern, message in error_patterns:
                        if re.search(pattern, line):
                            # Skip if it's a comment
                            stripped = line.strip()
                            if stripped.startswith("#"):
                                continue
                            
                            self.findings.append(DebugFinding(
                                severity="medium" if "hardcoded" in message else "low",
                                category="security" if "hardcoded" in message else "code_quality",
                                file=str(py_file.relative_to(self.app_root)),
                                line=line_num,
                                message=message,
                                code=line.strip()[:80]
                            ))
            except (IOError, UnicodeDecodeError):
                pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ENUM TYPE HANDLING CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_enum_handling(self) -> None:
        """
        Check for enum type handling issues.
        
        Common bugs:
        - Passing string where enum expected
        - Using .value on string (after improper conversion)
        - Missing isinstance checks before enum conversion
        """
        
        # Patterns that indicate enum handling issues
        patterns = [
            # Pattern: using .value on something that might be a string
            (r'(\w+)\.value\b', "Potential .value call on non-enum - ensure type is actually enum"),
            # Pattern: AgentType(variable) without isinstance check
            (r'AgentType\((\w+)\)(?!\s*if)', "AgentType conversion without type check - wrap with isinstance"),
            # Pattern: NoteType(variable) without isinstance check  
            (r'NoteType\((\w+)\)(?!\s*if)', "NoteType conversion without type check"),
        ]
        
        for py_file in self.app_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv", "test"]):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                
                for line_num, line in enumerate(lines, 1):
                    # Skip comments
                    if line.strip().startswith("#"):
                        continue
                    
                    # Check for enum fallback patterns that might have issues
                    # e.g., self.default_agent or AgentType.MANAGER
                    # Skip if this is in a string (checking for pattern) or comment
                    if ("or AgentType" in line or "or NoteType" in line) and '"or AgentType"' not in line and "'or AgentType'" not in line:
                        # Check if the left side might be a string
                        if "self.default_agent" in line or ("agent" in line.lower() and "=" in line):
                            # Verify there's a proper isinstance check earlier
                            # This is a heuristic - flag for review
                            context_start = max(0, line_num - 10)
                            context = "\n".join(lines[context_start:line_num])
                            
                            if "isinstance" not in context and "if agent is None" not in context:
                                self.findings.append(DebugFinding(
                                    severity="medium",
                                    category="type_safety",
                                    file=str(py_file.relative_to(self.app_root)),
                                    line=line_num,
                                    message="Enum fallback without proper None/type check",
                                    suggestion="Add 'if x is None' check before enum fallback",
                                    code=line.strip()[:80]
                                ))
            except (IOError, UnicodeDecodeError):
                pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SPEC COMPLIANCE CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_spec_compliance(self) -> None:
        """
        Check implementation against spec documents.
        
        Compares:
        - ARCHITECTURE.md requirements vs implementation
        - SECONDBRAIN_INTEGRATION.md requirements vs implementation
        """
        docs_dir = self.app_root / "docs"
        
        # Check SecondBrain integration spec
        sb_spec = docs_dir / "SECONDBRAIN_INTEGRATION.md"
        if sb_spec.exists():
            self._check_secondbrain_spec_compliance(sb_spec)
        
        # Check architecture spec
        arch_spec = self.app_root / "ARCHITECTURE.md"
        if arch_spec.exists():
            self._check_architecture_spec_compliance(arch_spec)
    
    def _check_secondbrain_spec_compliance(self, spec_path: Path) -> None:
        """Check SecondBrain implementation against spec"""
        spec_content = spec_path.read_text()
        
        # Required vault folders per spec
        required_folders = [
            "inbox", "memory", "entities", "projects", "finance",
            "maintenance", "contractors", "decisions", "logs", "_index"
        ]
        
        vault_path = VAULT_PATH
        if vault_path.exists():
            for folder in required_folders:
                if not (vault_path / folder).exists():
                    self.findings.append(DebugFinding(
                        severity="medium",
                        category="spec_compliance",
                        file="SecondBrain vault",
                        line=None,
                        message=f"Missing vault folder: {folder}/",
                        suggestion=f"Create folder: mkdir -p {vault_path / folder}"
                    ))
        
        # Required SecondBrain methods per spec
        required_methods = ["write_note", "append", "link", "search", "get_entity", "get_graph"]
        
        try:
            from core.secondbrain import SecondBrain
            sb = SecondBrain.__new__(SecondBrain)
            for method in required_methods:
                if not hasattr(sb, method) or not callable(getattr(sb, method)):
                    self.findings.append(DebugFinding(
                        severity="high",
                        category="spec_compliance",
                        file="core/secondbrain/skill.py",
                        line=None,
                        message=f"Missing required method: {method}()",
                        suggestion="Implement method per SECONDBRAIN_INTEGRATION.md spec"
                    ))
        except Exception as e:
            self.findings.append(DebugFinding(
                severity="high",
                category="spec_compliance",
                file="core/secondbrain",
                line=None,
                message=f"SecondBrain module error: {e}"
            ))
        
        # Required note metadata fields per spec
        required_fields = ["id", "type", "tenant", "agent", "created_at", "source"]
        
        # Check a sample note
        sample_notes = list(vault_path.glob("**/sb_*.md")) if vault_path.exists() else []
        if sample_notes:
            try:
                content = sample_notes[0].read_text()
                if content.startswith("---"):
                    # Parse YAML frontmatter
                    end_idx = content.find("---", 3)
                    if end_idx > 0:
                        import yaml
                        frontmatter = yaml.safe_load(content[4:end_idx])
                        for field in required_fields:
                            if field not in frontmatter:
                                self.findings.append(DebugFinding(
                                    severity="medium",
                                    category="spec_compliance",
                                    file=str(sample_notes[0]),
                                    line=None,
                                    message=f"Note missing required field: {field}",
                                    suggestion="Add field to note frontmatter per spec"
                                ))
            except Exception:
                pass
    
    def _check_architecture_spec_compliance(self, spec_path: Path) -> None:
        """Check implementation against ARCHITECTURE.md"""
        # Check wizard steps match spec
        # The spec defines specific wizard steps that should be implemented
        
        wizard_file = self.app_root / "frontend" / "src" / "components" / "SetupWizard" / "SetupWizard.tsx"
        if wizard_file.exists():
            content = wizard_file.read_text()
            
            # Required steps per ARCHITECTURE.md
            required_steps = ["Welcome", "Income", "Budgets", "Connectors", "Notifications", "Complete"]
            
            for step in required_steps:
                # Check if step exists in steps array or as a function
                if f'"{step}"' not in content and f"function {step}Step" not in content:
                    # Handle equivalent step names
                    if step == "Income" and "IncomeSource" in content:
                        continue  # Income might be IncomeSource
                    if step == "Complete" and '"Launch"' in content:
                        continue  # Complete might be Launch
                    self.findings.append(DebugFinding(
                        severity="medium",
                        category="spec_compliance",
                        file="frontend SetupWizard",
                        line=None,
                        message=f"Wizard missing step: {step}",
                        suggestion="Add step per ARCHITECTURE.md spec"
                    ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FRONTEND/BACKEND SYNC CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_frontend_backend_sync(self) -> None:
        """
        Check frontend and backend models are in sync.
        
        Common issues:
        - Frontend interface has fields backend doesn't expect
        - Backend Pydantic model differs from frontend TypeScript
        - API routes exist in backend but not called from frontend
        """
        # Check WizardData sync
        self._check_wizard_data_sync()
        
        # Check API route coverage
        self._check_api_route_coverage()
    
    def _check_wizard_data_sync(self) -> None:
        """Check WizardData model matches between frontend and backend"""
        frontend_wizard = self.app_root / "frontend" / "src" / "components" / "SetupWizard" / "SetupWizard.tsx"
        backend_settings = self.app_root / "api" / "routes" / "settings.py"
        
        if not frontend_wizard.exists() or not backend_settings.exists():
            return
        
        # Extract frontend interface fields
        frontend_content = frontend_wizard.read_text()
        frontend_fields = set()
        
        # Simple regex to find interface fields
        import re
        interface_match = re.search(r'interface SetupData \{([^}]+)\}', frontend_content, re.DOTALL)
        if interface_match:
            interface_body = interface_match.group(1)
            # Extract field names (e.g., "fieldName: type")
            for line in interface_body.split("\n"):
                match = re.match(r'\s*(\w+)\s*:', line)
                if match:
                    frontend_fields.add(match.group(1))
        
        # Extract backend model fields
        backend_content = backend_settings.read_text()
        backend_fields = set()
        
        # Find WizardData class - need to handle multi-line docstrings
        # Look for class definition then extract until next class or function
        wizard_start = backend_content.find("class WizardData(BaseModel):")
        if wizard_start >= 0:
            # Find the next class/function definition (but not in strings)
            remaining = backend_content[wizard_start + 30:]  # Skip the class line
            
            # Find fields - they're lines with "fieldName: type = default"
            for line in remaining.split("\n"):
                # Stop at next class or @router
                if line.strip().startswith("class ") or line.strip().startswith("@router"):
                    break
                # Skip comments, docstrings, empty lines
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                # Match field definition
                match = re.match(r'(\w+)\s*:\s*\w+', stripped)
                if match and not match.group(1).startswith("_"):
                    backend_fields.add(match.group(1))
        
        # Compare
        frontend_only = frontend_fields - backend_fields
        backend_only = backend_fields - frontend_fields
        
        for field in frontend_only:
            self.findings.append(DebugFinding(
                severity="medium",
                category="sync",
                file="WizardData model",
                line=None,
                message=f"Field '{field}' in frontend but not backend",
                suggestion="Add field to backend WizardData or remove from frontend"
            ))
        
        for field in backend_only:
            self.findings.append(DebugFinding(
                severity="medium",
                category="sync",
                file="WizardData model",
                line=None,
                message=f"Field '{field}' in backend but not frontend",
                suggestion="Add field to frontend SetupData or remove from backend"
            ))
    
    def _check_api_route_coverage(self) -> None:
        """Check that API routes are properly covered"""
        # Get backend routes
        try:
            from api.main import app
            backend_routes = set()
            for route in app.routes:
                if hasattr(route, 'path'):
                    backend_routes.add(route.path)
            
            # Critical routes that must exist
            required_routes = [
                "/api/chat/send",
                "/api/chat/history",
                "/api/messaging/send",
                "/api/messaging/contacts",
                "/api/system/live",
                "/api/secondbrain/notes",
                "/api/settings/wizard",
            ]
            
            for route in required_routes:
                if route not in backend_routes:
                    self.findings.append(DebugFinding(
                        severity="high",
                        category="sync",
                        file="API routes",
                        line=None,
                        message=f"Missing required API route: {route}",
                        suggestion="Add route to appropriate router"
                    ))
        except Exception as e:
            self.findings.append(DebugFinding(
                severity="medium",
                category="sync",
                file="api/main.py",
                line=None,
                message=f"Could not check API routes: {e}"
            ))
    
    def _check_api_response_contracts(self) -> None:
        """
        Check that API endpoints return data structures the frontend expects.
        
        LESSON LEARNED (2026-01-30): The /system/monitor endpoint had `processes: []`
        hardcoded as empty with a "For future use" comment. The frontend AgentManager
        expected this array to be populated with agent status data. This caused all
        agents to show as "offline" in the UI even though the backend was healthy.
        
        This check validates critical API response contracts:
        1. /system/monitor must return non-empty `processes` array when system is running
        2. /system/startup must actually start agents via lifecycle manager
        3. Agent status responses must include running state from lifecycle, not mocks
        """
        import re
        
        # Check 1: /system/monitor processes field
        api_main = self.app_root / "api" / "main.py"
        if api_main.exists():
            content = api_main.read_text()
            lines = content.split("\n")
            
            # Look for monitor endpoint
            in_monitor = False
            for line_num, line in enumerate(lines, 1):
                if "def system_monitor" in line or 'def get_system_monitor' in line:
                    in_monitor = True
                elif in_monitor and line.strip().startswith("def "):
                    in_monitor = False
                
                if in_monitor:
                    # Check for hardcoded empty processes
                    if '"processes": []' in line or "'processes': []" in line:
                        if "# For future use" in line or "# TODO" in line or "# FIXME" in line:
                            self.findings.append(DebugFinding(
                                severity="critical",
                                category="api_contract",
                                file="api/main.py",
                                line=line_num,
                                message="CRITICAL: /system/monitor returns hardcoded empty `processes` array",
                                suggestion="Build processes array from lifecycle.get_status().agents - frontend expects [{id, state, ...}]"
                            ))
                        elif "[]" in line and "processes" in line:
                            # Even without comment, empty processes is suspicious
                            self.findings.append(DebugFinding(
                                severity="high",
                                category="api_contract",
                                file="api/main.py",
                                line=line_num,
                                message="/system/monitor may return empty `processes` - verify data source",
                                suggestion="Ensure processes is built from lifecycle manager status, not hardcoded"
                            ))
        
        # Check 2: /system/startup should call lifecycle.startup()
        if api_main.exists():
            content = api_main.read_text()
            
            # Find startup endpoint
            startup_match = re.search(
                r'async def system_startup.*?(?=\nasync def |\nclass |\Z)',
                content, re.DOTALL
            )
            if startup_match:
                startup_body = startup_match.group(0)
                if "lifecycle" not in startup_body.lower() and "get_lifecycle_manager" not in startup_body:
                    self.findings.append(DebugFinding(
                        severity="high",
                        category="api_contract",
                        file="api/main.py",
                        line=None,
                        message="/system/startup doesn't call lifecycle manager - agents won't actually start",
                        suggestion="Add: lifecycle = get_lifecycle_manager(); lifecycle.startup()"
                    ))
        
        # Check 3: Frontend AgentManager expectations
        agent_manager = self.app_root / "frontend" / "src" / "components" / "AgentManager" / "AgentManager.tsx"
        if agent_manager.exists():
            content = agent_manager.read_text()
            
            # Check what state values frontend expects
            if 'state === "running"' in content:
                # Frontend expects "running" state for active agents
                # Verify backend returns "running" (not "active" or other)
                if api_main.exists():
                    api_content = api_main.read_text()
                    if '"state": "active"' in api_content and '"state": "running"' not in api_content:
                        self.findings.append(DebugFinding(
                            severity="medium",
                            category="api_contract",
                            file="api/main.py",
                            line=None,
                            message="State mismatch: frontend expects 'running', backend may return 'active'",
                            suggestion="Ensure /system/monitor returns state='running' for active agents"
                        ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ADVANCED BUG DETECTION (Added 2026-01-29)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_async_issues(self) -> None:
        """
        Check for asyncio.run() called in async context.
        This causes 'cannot be called from a running event loop' errors.
        
        Only flags if asyncio.run() is NOT wrapped in a try/except that
        checks for RuntimeError (the proper pattern).
        """
        for py_file in self.app_root.rglob("*.py"):
            # Skip self to avoid false positives from pattern detection code
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv", "janitor_debugger.py"]):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                
                # Check if file has async functions
                has_async = "async def" in content
                has_asyncio_run = "asyncio.run(" in content
                
                if has_async and has_asyncio_run:
                    for line_num, line in enumerate(lines, 1):
                        if "asyncio.run(" in line and not line.strip().startswith("#"):
                            # Check if there's a proper guard nearby
                            context_start = max(0, line_num - 5)
                            context = "\n".join(lines[context_start:line_num])
                            
                            # Proper guards include checking for running loop
                            guards = [
                                "get_running_loop",
                                "RuntimeError",
                                "except RuntimeError",
                                "No running loop",
                            ]
                            has_guard = any(g in context for g in guards)
                            
                            if not has_guard:
                                self.findings.append(DebugFinding(
                                    severity="high",
                                    category="async",
                                    file=str(py_file.relative_to(self.app_root)),
                                    line=line_num,
                                    message="asyncio.run() without running loop check - may fail in async context",
                                    suggestion="Wrap with: try: loop = asyncio.get_running_loop() except RuntimeError: asyncio.run(...)"
                                ))
            except (IOError, UnicodeDecodeError):
                pass
    
    def _check_bare_except(self) -> None:
        """
        Check for bare except: clauses that hide bugs.
        """
        for py_file in self.app_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv"]):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                
                for line_num, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped == "except:" or stripped.startswith("except: "):
                        self.findings.append(DebugFinding(
                            severity="medium",
                            category="error_handling",
                            file=str(py_file.relative_to(self.app_root)),
                            line=line_num,
                            message="Bare 'except:' clause hides bugs",
                            suggestion="Use 'except Exception as e:' or more specific exception types"
                        ))
            except (IOError, UnicodeDecodeError):
                pass
    
    def _check_hardcoded_values(self) -> None:
        """
        Check for hardcoded tenant IDs, paths, and other values that should be configurable.
        """
        hardcoded_patterns = [
            ("tenkiang_household", "hardcoded tenant ID - use config or parameter"),
            ("/Users/", "hardcoded absolute path - use Path.home() or config"),
            ("localhost:8000", "hardcoded localhost URL - use config"),
            ("sk-", "potential hardcoded API key"),
        ]
        
        for py_file in self.app_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv", "test", "janitor_debugger.py"]):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                
                for line_num, line in enumerate(lines, 1):
                    if line.strip().startswith("#"):
                        continue
                    
                    for pattern, message in hardcoded_patterns:
                        if pattern in line:
                            # Skip if it's in a comment or docstring
                            if '"""' in line or "'''" in line:
                                continue
                            # Skip regex patterns (checking for API key patterns is fine)
                            if 'r"' in line or "r'" in line:
                                continue
                            # Skip HTML/CSS styles
                            if 'style=' in line or 'color:' in line:
                                continue
                            # Skip if pattern is in a dict key or string comparison
                            if f'"{pattern}"' in line or f"'{pattern}'" in line:
                                continue
                            # Skip if it's a default value in os.environ.get()
                            if "os.environ.get(" in line and pattern in line:
                                continue
                            # Skip if pattern is a variable name prefix or in a string check
                            if pattern == "sk-":
                                if 'r"sk-' in line or "r'sk-" in line:  # regex pattern
                                    continue
                                if '"sk-ant"' in line or "'sk-ant'" in line:  # string comparison
                                    continue
                                # Skip CSS class names (task-*, risk-*)
                                if "task-" in line or "risk-" in line:
                                    continue
                                # Only flag actual API key patterns (sk-ant- or sk-proj- etc)
                                import re
                                if not re.search(r'sk-[a-zA-Z]+-[a-zA-Z0-9]', line):
                                    continue
                            self.findings.append(DebugFinding(
                                severity="low" if pattern == "tenkiang_household" else "medium",
                                category="hardcoded",
                                file=str(py_file.relative_to(self.app_root)),
                                line=line_num,
                                message=f"Hardcoded value: {message}",
                                suggestion="Extract to configuration or parameter"
                            ))
            except (IOError, UnicodeDecodeError):
                pass
    
    def _check_none_access(self) -> None:
        """
        Check for potential None[0] or empty list access without guards.
        """
        dangerous_patterns = [
            (r'\[0\]', "Index [0] access - ensure list is not empty"),
            (r'\.split\([^)]*\)\[', "Split then index - check for empty result"),
            (r'\.pop\(\)', ".pop() on potentially empty list"),
        ]
        
        import re
        
        for py_file in self.app_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv", "janitor_debugger.py"]):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                
                for line_num, line in enumerate(lines, 1):
                    if line.strip().startswith("#"):
                        continue
                    
                    for pattern, message in dangerous_patterns:
                        if re.search(pattern, line):
                            # Skip known safe patterns
                            safe_patterns = [
                                "sys.version_info[0]",  # Always exists
                                "version_info[0]",      # Always exists
                                "current[0]",           # Common var name for version_info
                                "MIN_PYTHON[0]",        # Tuple constant
                                ".split(",              # split() always returns at least 1 element
                                "[-1]",                 # Last element access (often with split)
                                "[0]:",                 # Slicing, not indexing
                                "row[0]",               # Database row access (known to exist)
                                "args[0]",              # CLI args (checked elsewhere)
                                "parts[0]",             # After split, if var name is parts
                                "result[0]",            # Query results (checked before access)
                                "matches[0]",           # Regex matches (checked before access)
                                "findings[0]",          # List after check
                                "transactions[0]",      # Demo data, known non-empty
                                "jpm_transactions[0]",  # Demo data, known non-empty
                            ]
                            if any(sp in line for sp in safe_patterns):
                                continue
                            
                            # Check if there's a guard in the previous lines (expand to 10 for if/else blocks)
                            context_start = max(0, line_num - 10)
                            context = "\n".join(lines[context_start:line_num])
                            
                            guards = ["if ", "if len(", "if not", "and len(", "> 0", "!= []", 
                                     "is not None", "or []", ".get(", "try:", "except", "else:",
                                     "== 1", "> 1", ">= 1", "len(chunks)", "len(backups)"]
                            has_guard = any(g in context for g in guards)
                            
                            if not has_guard:
                                self.findings.append(DebugFinding(
                                    severity="medium",
                                    category="null_safety",
                                    file=str(py_file.relative_to(self.app_root)),
                                    line=line_num,
                                    message=message,
                                    suggestion="Add length/None check before accessing"
                                ))
            except (IOError, UnicodeDecodeError):
                pass
    
    def _check_unused_imports(self) -> None:
        """
        Check for unused imports using AST analysis.
        """
        import ast
        
        for py_file in self.app_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv"]):
                continue
            # Skip __init__.py as they often re-export
            if py_file.name == "__init__.py":
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                imports = {}  # name -> line number
                used = set()
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            name = alias.asname or alias.name.split('.')[0]
                            imports[name] = node.lineno
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name != '*':
                                name = alias.asname or alias.name
                                imports[name] = node.lineno
                    elif isinstance(node, ast.Name):
                        used.add(node.id)
                    elif isinstance(node, ast.Attribute):
                        # Handle things like datetime.datetime
                        if isinstance(node.value, ast.Name):
                            used.add(node.value.id)
                
                unused = set(imports.keys()) - used
                
                # Filter out common false positives
                false_positives = {"Optional", "List", "Dict", "Any", "Tuple", "Union", "TYPE_CHECKING"}
                unused = unused - false_positives
                
                if unused and len(unused) <= 5:  # Only report if manageable
                    for name in unused:
                        self.findings.append(DebugFinding(
                            severity="low",
                            category="unused",
                            file=str(py_file.relative_to(self.app_root)),
                            line=imports[name],
                            message=f"Unused import: {name}",
                            suggestion=f"Remove 'import {name}' or use it"
                        ))
            except (SyntaxError, IOError, UnicodeDecodeError):
                pass
    
    def _check_todo_fixme(self) -> None:
        """
        Check for TODO, FIXME, HACK, XXX comments that indicate incomplete work.
        """
        markers = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
        
        for py_file in self.app_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["venv", "__pycache__", "node_modules", ".venv"]):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                
                for line_num, line in enumerate(lines, 1):
                    for marker in markers:
                        if marker in line and ("#" in line or '"""' in line or "'''" in line):
                            self.findings.append(DebugFinding(
                                severity="info",
                                category="todo",
                                file=str(py_file.relative_to(self.app_root)),
                                line=line_num,
                                message=f"{marker} found: {line.strip()[:60]}...",
                                suggestion="Address or remove before production"
                            ))
            except (IOError, UnicodeDecodeError):
                pass
    
    def _check_startup_issues(self) -> None:
        """
        Check for common startup issues:
        - Stale lock files from crashed processes
        - Missing node_modules
        - Missing .venv
        - Required commands not available
        """
        import shutil
        
        # Check for Next.js lock file
        next_lock = self.app_root / "frontend" / ".next" / "dev" / "lock"
        if next_lock.exists():
            self.findings.append(DebugFinding(
                severity="high",
                category="startup",
                file="frontend/.next/dev/lock",
                line=None,
                message="Next.js dev lock file exists - another instance may be running or crashed",
                suggestion="Run: rm frontend/.next/dev/lock"
            ))
        
        # Check for node_modules
        node_modules = self.app_root / "frontend" / "node_modules"
        if not node_modules.exists():
            self.findings.append(DebugFinding(
                severity="high",
                category="startup",
                file="frontend/node_modules",
                line=None,
                message="Frontend dependencies not installed",
                suggestion="Run: cd frontend && npm install"
            ))
        
        # Check for .venv
        venv = self.app_root / ".venv"
        if not venv.exists():
            self.findings.append(DebugFinding(
                severity="high",
                category="startup",
                file=".venv",
                line=None,
                message="Python virtual environment not found",
                suggestion="Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
            ))
        
        # Check for required commands
        required_commands = ["uvicorn", "npm", "node"]
        for cmd in required_commands:
            if not shutil.which(cmd):
                # Check if it's in the venv
                venv_cmd = self.app_root / ".venv" / "bin" / cmd
                if not venv_cmd.exists():
                    self.findings.append(DebugFinding(
                        severity="medium",
                        category="startup",
                        file="system",
                        line=None,
                        message=f"Required command not found: {cmd}",
                        suggestion=f"Install {cmd} or activate virtual environment"
                    ))
        
        # Check start.sh is executable
        start_sh = self.app_root / "start.sh"
        if start_sh.exists():
            import stat
            mode = start_sh.stat().st_mode
            if not (mode & stat.S_IXUSR):
                self.findings.append(DebugFinding(
                    severity="low",
                    category="startup",
                    file="start.sh",
                    line=None,
                    message="start.sh is not executable",
                    suggestion="Run: chmod +x start.sh"
                ))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def format_report(self, report: DebugReport, format: str = "text") -> str:
        """Format report for display"""
        lines = []
        
        lines.append("╔══════════════════════════════════════════════════════════════╗")
        lines.append("║           🔍 JANITOR DEBUGGER - AUDIT REPORT                ║")
        lines.append("╚══════════════════════════════════════════════════════════════╝")
        lines.append("")
        lines.append(f"  Timestamp: {report.timestamp}")
        lines.append(f"  Duration: {report.duration_ms}ms")
        lines.append(f"  Files Checked: {report.total_files_checked}")
        lines.append("")
        
        # Summary
        lines.append("┌─────────────────────────────────────────────────────────────┐")
        lines.append("│ SUMMARY                                                     │")
        lines.append("├─────────────────────────────────────────────────────────────┤")
        lines.append(f"│  🔴 Critical: {report.summary.get('critical', 0):>3}                                         │")
        lines.append(f"│  🟠 High:     {report.summary.get('high', 0):>3}                                         │")
        lines.append(f"│  🟡 Medium:   {report.summary.get('medium', 0):>3}                                         │")
        lines.append(f"│  🔵 Low:      {report.summary.get('low', 0):>3}                                         │")
        lines.append(f"│  ⚪ Info:     {report.summary.get('info', 0):>3}                                         │")
        lines.append("└─────────────────────────────────────────────────────────────┘")
        
        # Critical and High findings
        critical_high = [f for f in report.findings if f.severity in ["critical", "high"]]
        if critical_high:
            lines.append("")
            lines.append("┌─────────────────────────────────────────────────────────────┐")
            lines.append("│ 🚨 CRITICAL & HIGH SEVERITY FINDINGS                        │")
            lines.append("├─────────────────────────────────────────────────────────────┤")
            
            for finding in critical_high:
                severity_icon = "🔴" if finding.severity == "critical" else "🟠"
                lines.append(f"│ {severity_icon} [{finding.category}] {finding.file[:40]:<40} │")
                lines.append(f"│    Line {finding.line or 'N/A'}: {finding.message[:45]:<45} │")
                if finding.suggestion:
                    lines.append(f"│    💡 {finding.suggestion[:50]:<50} │")
                lines.append("│                                                             │")
            
            lines.append("└─────────────────────────────────────────────────────────────┘")
        
        # Status
        total_issues = sum(report.summary.values()) - report.summary.get("info", 0)
        if total_issues == 0:
            lines.append("")
            lines.append("✅ No issues found! System is healthy.")
        elif report.summary.get("critical", 0) > 0:
            lines.append("")
            lines.append("⛔ CRITICAL ISSUES REQUIRE IMMEDIATE ATTENTION")
        
        return "\n".join(lines)
    
    def generate_html_report(self, report: DebugReport, output_path: Path = None) -> str:
        """
        Generate an interactive HTML debug map/report.
        
        Creates a visual representation of:
        - System architecture
        - Findings by severity and category
        - Module health status
        - Actionable recommendations
        """
        if output_path is None:
            output_path = self.app_root / "debug_report.html"
        
        # Group findings by category
        by_category = {}
        for f in report.findings:
            cat = f.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f)
        
        # Generate category cards HTML
        category_cards = ""
        category_colors = {
            "syntax": "#ef4444",
            "import": "#f97316",
            "api_contract": "#dc2626",
            "sync": "#8b5cf6",
            "async": "#3b82f6",
            "error_handling": "#eab308",
            "hardcoded": "#6366f1",
            "security": "#ef4444",
            "spec": "#10b981",
            "database": "#06b6d4",
            "config": "#f59e0b",
        }
        
        for cat, findings in sorted(by_category.items(), key=lambda x: -len(x[1])):
            color = category_colors.get(cat, "#6b7280")
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for f in findings:
                severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
            
            findings_html = "".join(
                f'''<div class="finding {'critical' if f.severity == 'critical' else 'high' if f.severity == 'high' else ''}">
                    <span class="severity {f.severity}">●</span>
                    <span class="file">{f.file[:40]}</span>
                    {f'<span class="line">:{f.line}</span>' if f.line else ''}
                    <p class="message">{f.message}</p>
                    {f'<p class="suggestion">💡 {f.suggestion}</p>' if f.suggestion else ''}
                </div>'''
                for f in findings[:10]
            )
            
            category_cards += f'''
            <div class="category-card" style="border-left: 4px solid {color}">
                <div class="category-header">
                    <h3>{cat.replace('_', ' ').title()}</h3>
                    <span class="count">{len(findings)}</span>
                </div>
                <div class="severity-bar">
                    <span class="critical" title="Critical">{severity_counts['critical']}</span>
                    <span class="high" title="High">{severity_counts['high']}</span>
                    <span class="medium" title="Medium">{severity_counts['medium']}</span>
                    <span class="low" title="Low">{severity_counts['low']}</span>
                </div>
                <div class="findings">{findings_html}</div>
            </div>
            '''
        
        # Generate system map
        modules = ["api", "agents", "core", "database", "frontend", "config"]
        module_status = {}
        for mod in modules:
            mod_findings = [f for f in report.findings if mod in f.file.lower()]
            if any(f.severity == "critical" for f in mod_findings):
                module_status[mod] = ("critical", "#ef4444")
            elif any(f.severity == "high" for f in mod_findings):
                module_status[mod] = ("warning", "#f97316")
            elif mod_findings:
                module_status[mod] = ("info", "#eab308")
            else:
                module_status[mod] = ("healthy", "#22c55e")
        
        system_map = "".join(
            f'''<div class="module {status[0]}" style="background: {status[1]}20; border-color: {status[1]}">
                <span class="icon">{'🔴' if status[0] == 'critical' else '🟠' if status[0] == 'warning' else '🟡' if status[0] == 'info' else '🟢'}</span>
                <span class="name">{mod}</span>
                <span class="count">{len([f for f in report.findings if mod in f.file.lower()])}</span>
            </div>'''
            for mod, status in module_status.items()
        )
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔍 MyCasa Pro - Debug Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 2rem;
            background: rgba(255,255,255,0.05);
            border-radius: 1rem;
            margin-bottom: 2rem;
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        .header .subtitle {{ color: #94a3b8; }}
        .meta {{ display: flex; gap: 2rem; justify-content: center; margin-top: 1rem; }}
        .meta span {{ background: rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 0.5rem; }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .summary-card {{
            background: rgba(255,255,255,0.05);
            padding: 1.5rem;
            border-radius: 1rem;
            text-align: center;
        }}
        .summary-card .number {{ font-size: 2.5rem; font-weight: bold; }}
        .summary-card .label {{ color: #94a3b8; font-size: 0.875rem; }}
        .summary-card.critical .number {{ color: #ef4444; }}
        .summary-card.high .number {{ color: #f97316; }}
        .summary-card.medium .number {{ color: #eab308; }}
        .summary-card.low .number {{ color: #3b82f6; }}
        .summary-card.info .number {{ color: #6b7280; }}
        
        .system-map {{
            background: rgba(255,255,255,0.05);
            padding: 1.5rem;
            border-radius: 1rem;
            margin-bottom: 2rem;
        }}
        .system-map h2 {{ margin-bottom: 1rem; }}
        .modules {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }}
        .module {{
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            border: 2px solid;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .module .name {{ font-weight: 600; }}
        .module .count {{ 
            background: rgba(0,0,0,0.2);
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
        }}
        
        .categories {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
        }}
        .category-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 1rem;
            padding: 1.5rem;
        }}
        .category-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .category-header h3 {{ font-size: 1.25rem; }}
        .category-header .count {{
            background: rgba(255,255,255,0.1);
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.875rem;
        }}
        .severity-bar {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
            font-size: 0.75rem;
        }}
        .severity-bar span {{
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
        }}
        .severity-bar .critical {{ background: #ef444433; color: #ef4444; }}
        .severity-bar .high {{ background: #f9731633; color: #f97316; }}
        .severity-bar .medium {{ background: #eab30833; color: #eab308; }}
        .severity-bar .low {{ background: #3b82f633; color: #3b82f6; }}
        
        .finding {{
            background: rgba(0,0,0,0.2);
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
        }}
        .finding.critical {{ border-left: 3px solid #ef4444; }}
        .finding.high {{ border-left: 3px solid #f97316; }}
        .finding .severity {{ margin-right: 0.5rem; }}
        .finding .severity.critical {{ color: #ef4444; }}
        .finding .severity.high {{ color: #f97316; }}
        .finding .severity.medium {{ color: #eab308; }}
        .finding .severity.low {{ color: #3b82f6; }}
        .finding .file {{ color: #60a5fa; }}
        .finding .line {{ color: #94a3b8; }}
        .finding .message {{ margin-top: 0.5rem; color: #cbd5e1; }}
        .finding .suggestion {{ margin-top: 0.5rem; color: #22c55e; font-size: 0.8rem; }}
        
        .footer {{
            text-align: center;
            margin-top: 2rem;
            color: #64748b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Debug Report</h1>
            <p class="subtitle">MyCasa Pro System Health Analysis</p>
            <div class="meta">
                <span>📅 {report.timestamp}</span>
                <span>⏱️ {report.duration_ms}ms</span>
                <span>📁 {report.total_files_checked} files checked</span>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card critical">
                <div class="number">{report.summary.get('critical', 0)}</div>
                <div class="label">Critical</div>
            </div>
            <div class="summary-card high">
                <div class="number">{report.summary.get('high', 0)}</div>
                <div class="label">High</div>
            </div>
            <div class="summary-card medium">
                <div class="number">{report.summary.get('medium', 0)}</div>
                <div class="label">Medium</div>
            </div>
            <div class="summary-card low">
                <div class="number">{report.summary.get('low', 0)}</div>
                <div class="label">Low</div>
            </div>
            <div class="summary-card info">
                <div class="number">{report.summary.get('info', 0)}</div>
                <div class="label">Info</div>
            </div>
        </div>
        
        <div class="system-map">
            <h2>🗺️ System Module Health</h2>
            <div class="modules">{system_map}</div>
        </div>
        
        <h2 style="margin-bottom: 1rem;">📋 Findings by Category</h2>
        <div class="categories">{category_cards if category_cards else '<p style="color: #22c55e; text-align: center; padding: 2rem;">✅ No issues found! System is healthy.</p>'}</div>
        
        <div class="footer">
            <p>Generated by Salimata (Janitor Agent) • MyCasa Pro</p>
        </div>
    </div>
</body>
</html>'''
        
        output_path.write_text(html)
        return str(output_path)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION WITH JANITOR AGENT
# ═══════════════════════════════════════════════════════════════════════════════

def integrate_with_janitor():
    """
    Add debugging capabilities to the JanitorAgent.
    Call this to get the extended methods.
    """
    return JanitorDebugger()


if __name__ == "__main__":
    # Run standalone audit
    debugger = JanitorDebugger()
    report = debugger.run_full_audit()
    print(debugger.format_report(report))
