"""
Clawdbot Runner - Execute Clawdbot CLI commands with streaming output.

This is the BRAIN. It gives the Manager the same power as the terminal.
"""
import asyncio
import shlex
import uuid
import os
from datetime import datetime
from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class EventType(Enum):
    """Event types for command execution"""
    COMMAND_STARTED = "command_started"
    STDOUT_CHUNK = "stdout_chunk"
    STDERR_CHUNK = "stderr_chunk"
    COMMAND_FINISHED = "command_finished"
    TASK_QUEUED = "task_queued"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    COST_INCURRED = "cost_incurred"
    BUDGET_WARNING = "budget_warning"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_FINISHED = "tool_call_finished"


@dataclass
class CommandEvent:
    """Event emitted during command execution"""
    event_type: EventType
    timestamp: datetime
    command_id: str
    session_id: str
    
    # Content (varies by event type)
    data: Optional[str] = None
    exit_code: Optional[int] = None
    progress: Optional[float] = None
    error: Optional[str] = None
    cost: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return {
            "type": self.event_type.value,
            "ts": self.timestamp.isoformat(),
            "command_id": self.command_id,
            "session_id": self.session_id,
            "data": self.data,
            "exit_code": self.exit_code,
            "progress": self.progress,
            "error": self.error,
            "cost": self.cost,
            "meta": self.metadata
        }


@dataclass
class ExecutionContext:
    """Context for command execution"""
    user_id: str = "default"
    session_id: str = "main"
    permissions: set = field(default_factory=lambda: {"*"})  # All permissions by default
    workspace_path: Path = field(default_factory=lambda: Path.home() / "clawd")
    env_overrides: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 600
    stream_output: bool = True
    thinking_level: str = "low"  # off|minimal|low|medium|high
    verbose: bool = False
    deliver: bool = False  # Whether to deliver response to channel


class ClawdbotRunner:
    """
    Execute Clawdbot CLI commands with full power.
    
    This is the same as running commands in terminal - no restrictions,
    full tool access, streaming output.
    """
    
    def __init__(self, clawdbot_path: str = "clawdbot"):
        self.clawdbot_path = clawdbot_path
        self.running_processes: Dict[str, asyncio.subprocess.Process] = {}
    
    def generate_command_id(self) -> str:
        """Generate unique command ID"""
        return f"cmd_{uuid.uuid4().hex[:12]}"
    
    async def run_message(
        self,
        message: str,
        context: Optional[ExecutionContext] = None
    ) -> AsyncIterator[CommandEvent]:
        """
        Send a message to the Clawdbot agent and stream the response.
        
        This is equivalent to: clawdbot agent -m "message" --session-id main
        """
        context = context or ExecutionContext()
        
        # Build the command - MUST include --session-id or --agent
        cmd_parts = [
            self.clawdbot_path, "agent",
            "-m", message,
            "--session-id", context.session_id,  # Required!
            "--thinking", context.thinking_level,
        ]
        
        if context.verbose:
            cmd_parts.extend(["--verbose", "on"])
        
        if context.deliver:
            cmd_parts.append("--deliver")
        
        async for event in self.run_command(cmd_parts, context):
            yield event
    
    async def run_raw(
        self,
        command_string: str,
        context: Optional[ExecutionContext] = None
    ) -> AsyncIterator[CommandEvent]:
        """
        Run any raw Clawdbot command.
        
        Examples:
          - "status"
          - "sessions"
          - "agent -m 'hello'"
          - "cron list"
          - "browser screenshot"
        """
        context = context or ExecutionContext()
        
        # Parse the command string
        args = shlex.split(command_string)
        
        # If starts with "clawdbot", strip it
        if args and args[0] == "clawdbot":
            args = args[1:]
        
        cmd_parts = [self.clawdbot_path] + args
        
        async for event in self.run_command(cmd_parts, context):
            yield event
    
    async def run_command(
        self,
        cmd_parts: List[str],
        context: ExecutionContext
    ) -> AsyncIterator[CommandEvent]:
        """
        Execute a command and stream events.
        
        This is the core execution method.
        """
        command_id = self.generate_command_id()
        command_str = " ".join(cmd_parts)
        
        # Emit start event
        yield CommandEvent(
            event_type=EventType.COMMAND_STARTED,
            timestamp=datetime.utcnow(),
            command_id=command_id,
            session_id=context.session_id,
            metadata={"command": command_str, "args": cmd_parts[1:]}
        )
        
        try:
            # Set up environment
            env = os.environ.copy()
            env.update(context.env_overrides)
            
            # Create subprocess with PTY for proper terminal behavior
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(context.workspace_path)
            )
            
            self.running_processes[command_id] = process
            
            # Stream stdout and stderr concurrently
            async def read_stream(stream, event_type: EventType):
                """Read from a stream and yield events"""
                buffer = ""
                while True:
                    chunk = await stream.read(1024)
                    if not chunk:
                        break
                    
                    text = chunk.decode('utf-8', errors='replace')
                    buffer += text
                    
                    # Yield complete lines or when buffer gets big
                    while '\n' in buffer or len(buffer) > 500:
                        if '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            yield CommandEvent(
                                event_type=event_type,
                                timestamp=datetime.utcnow(),
                                command_id=command_id,
                                session_id=context.session_id,
                                data=line + '\n'
                            )
                        else:
                            # Yield partial buffer
                            yield CommandEvent(
                                event_type=event_type,
                                timestamp=datetime.utcnow(),
                                command_id=command_id,
                                session_id=context.session_id,
                                data=buffer
                            )
                            buffer = ""
                
                # Yield remaining buffer
                if buffer:
                    yield CommandEvent(
                        event_type=event_type,
                        timestamp=datetime.utcnow(),
                        command_id=command_id,
                        session_id=context.session_id,
                        data=buffer
                    )
            
            # Create tasks for both streams
            stdout_events = []
            stderr_events = []
            
            async def collect_stdout():
                async for event in read_stream(process.stdout, EventType.STDOUT_CHUNK):
                    stdout_events.append(event)
            
            async def collect_stderr():
                async for event in read_stream(process.stderr, EventType.STDERR_CHUNK):
                    stderr_events.append(event)
            
            # Run both collection tasks with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(collect_stdout(), collect_stderr()),
                    timeout=context.timeout_seconds
                )
            except asyncio.TimeoutError:
                process.kill()
                yield CommandEvent(
                    event_type=EventType.TASK_FAILED,
                    timestamp=datetime.utcnow(),
                    command_id=command_id,
                    session_id=context.session_id,
                    error=f"Command timed out after {context.timeout_seconds}s"
                )
                return
            
            # Interleave and yield all collected events
            all_events = sorted(
                stdout_events + stderr_events,
                key=lambda e: e.timestamp
            )
            for event in all_events:
                yield event
            
            # Wait for process to finish
            exit_code = await process.wait()
            
            yield CommandEvent(
                event_type=EventType.COMMAND_FINISHED,
                timestamp=datetime.utcnow(),
                command_id=command_id,
                session_id=context.session_id,
                exit_code=exit_code
            )
            
        except Exception as e:
            yield CommandEvent(
                event_type=EventType.TASK_FAILED,
                timestamp=datetime.utcnow(),
                command_id=command_id,
                session_id=context.session_id,
                error=str(e)
            )
        
        finally:
            # Clean up
            if command_id in self.running_processes:
                del self.running_processes[command_id]
    
    async def cancel(self, command_id: str) -> bool:
        """Cancel a running command"""
        if command_id in self.running_processes:
            process = self.running_processes[command_id]
            process.kill()
            return True
        return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status of running commands"""
        return {
            "running_commands": list(self.running_processes.keys()),
            "count": len(self.running_processes)
        }


# Singleton instance
_runner: Optional[ClawdbotRunner] = None


def get_runner() -> ClawdbotRunner:
    """Get the global Clawdbot runner instance"""
    global _runner
    if _runner is None:
        _runner = ClawdbotRunner()
    return _runner


async def run_clawdbot_message(message: str, **kwargs) -> str:
    """
    Convenience function: Run a message through Clawdbot and return full response.
    
    For simple cases where you don't need streaming.
    """
    runner = get_runner()
    context = ExecutionContext(**kwargs) if kwargs else None
    
    output = []
    exit_code = 0
    
    async for event in runner.run_message(message, context):
        if event.event_type == EventType.STDOUT_CHUNK and event.data:
            output.append(event.data)
        elif event.event_type == EventType.STDERR_CHUNK and event.data:
            output.append(f"[stderr] {event.data}")
        elif event.event_type == EventType.COMMAND_FINISHED:
            exit_code = event.exit_code or 0
        elif event.event_type == EventType.TASK_FAILED:
            output.append(f"[error] {event.error}")
            exit_code = 1
    
    return "".join(output)


async def run_clawdbot_command(command: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function: Run any Clawdbot command and return result.
    """
    runner = get_runner()
    context = ExecutionContext(**kwargs) if kwargs else None
    
    stdout = []
    stderr = []
    exit_code = 0
    error = None
    
    async for event in runner.run_raw(command, context):
        if event.event_type == EventType.STDOUT_CHUNK and event.data:
            stdout.append(event.data)
        elif event.event_type == EventType.STDERR_CHUNK and event.data:
            stderr.append(event.data)
        elif event.event_type == EventType.COMMAND_FINISHED:
            exit_code = event.exit_code or 0
        elif event.event_type == EventType.TASK_FAILED:
            error = event.error
            exit_code = 1
    
    return {
        "stdout": "".join(stdout),
        "stderr": "".join(stderr),
        "exit_code": exit_code,
        "error": error,
        "success": exit_code == 0 and not error
    }
