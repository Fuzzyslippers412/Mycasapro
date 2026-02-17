"""
Agent Teams - Multi-Agent Collaboration System
Enables coordinated work between specialized agents
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class TeamMode(str, Enum):
    """How team members execute tasks"""
    SEQUENTIAL = "sequential"  # One after another, output feeds next
    PARALLEL = "parallel"      # All at once, results merged
    CONSENSUS = "consensus"    # All vote, majority wins
    HIERARCHICAL = "hierarchical"  # Leader delegates, reviews results
    ROUND_ROBIN = "round_robin"  # Tasks distributed in rotation


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class TeamTask:
    """A task being executed by a team"""
    id: str
    description: str
    team_id: str
    mode: TeamMode
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: TaskStatus = TaskStatus.PENDING
    assigned_agents: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    final_result: Optional[Any] = None
    context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Other task IDs
    timeout_seconds: int = 300
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "mode": self.mode.value,
            "status": self.status.value,
        }


@dataclass 
class AgentTeam:
    """A configured team of agents for specific workflows"""
    id: str
    name: str
    description: str
    members: List[str]  # Agent IDs
    leader: str  # Primary coordinator
    mode: TeamMode
    emoji: str = "👥"
    
    # Optional configuration
    auto_escalate: bool = True  # Escalate to manager on failure
    require_consensus_threshold: float = 0.6  # For consensus mode
    max_parallel: int = 5  # Max concurrent agents for parallel mode
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "mode": self.mode.value,
        }


# Pre-configured teams for common workflows
PRESET_TEAMS: Dict[str, AgentTeam] = {
    "finance_review": AgentTeam(
        id="finance_review",
        name="Finance Review Team",
        description="Review transactions, validate budgets, spot anomalies",
        members=["finance", "janitor", "manager"],
        leader="finance",
        mode=TeamMode.SEQUENTIAL,
        emoji="💰",
    ),
    "maintenance_dispatch": AgentTeam(
        id="maintenance_dispatch", 
        name="Maintenance Dispatch Team",
        description="Handle repair requests, find contractors, schedule work",
        members=["maintenance", "contractors", "manager"],
        leader="maintenance",
        mode=TeamMode.HIERARCHICAL,
        emoji="🔧",
    ),
    "security_incident": AgentTeam(
        id="security_incident",
        name="Security Response Team",
        description="Respond to security incidents, assess damage, coordinate response",
        members=["security", "maintenance", "manager"],
        leader="security",
        mode=TeamMode.SEQUENTIAL,
        emoji="🚨",
    ),
    "project_planning": AgentTeam(
        id="project_planning",
        name="Project Planning Team",
        description="Plan home improvements, estimate costs, find contractors",
        members=["projects", "finance", "contractors", "manager"],
        leader="projects",
        mode=TeamMode.CONSENSUS,
        emoji="📋",
    ),
    "system_health": AgentTeam(
        id="system_health",
        name="System Health Team",
        description="Monitor system health, run audits, fix issues",
        members=["janitor", "manager"],
        leader="janitor",
        mode=TeamMode.SEQUENTIAL,
        emoji="🏥",
    ),
    "full_house_review": AgentTeam(
        id="full_house_review",
        name="Full House Review",
        description="Complete household status review from all domains",
        members=["finance", "maintenance", "security", "contractors", "projects", "janitor"],
        leader="manager",
        mode=TeamMode.PARALLEL,
        emoji="🏠",
    ),
    "emergency_response": AgentTeam(
        id="emergency_response",
        name="Emergency Response Team",
        description="Handle urgent issues requiring immediate multi-agent coordination",
        members=["security", "maintenance", "contractors", "manager"],
        leader="manager",
        mode=TeamMode.HIERARCHICAL,
        emoji="⚡",
        auto_escalate=True,
    ),
    "budget_decision": AgentTeam(
        id="budget_decision",
        name="Budget Decision Team",
        description="Make financial decisions requiring consensus",
        members=["finance", "maintenance", "projects", "manager"],
        leader="finance",
        mode=TeamMode.CONSENSUS,
        emoji="💵",
        require_consensus_threshold=0.75,
    ),
}


class TeamOrchestrator:
    """
    Orchestrates multi-agent team collaboration.
    
    Responsibilities:
    - Spawn team workflows
    - Route tasks between team members
    - Collect and merge results
    - Handle failures and escalation
    - Track team task history
    """
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data" / "teams"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._active_tasks: Dict[str, TeamTask] = {}
        self._task_history: List[Dict[str, Any]] = []
        self._custom_teams: Dict[str, AgentTeam] = {}
        
        self._load_state()
    
    def _load_state(self):
        """Load persisted team state"""
        state_file = self.data_dir / "orchestrator_state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    self._task_history = state.get("task_history", [])[-500:]
                    
                    # Load custom teams
                    for team_data in state.get("custom_teams", []):
                        team_data["mode"] = TeamMode(team_data["mode"])
                        team = AgentTeam(**team_data)
                        self._custom_teams[team.id] = team
            except Exception as e:
                print(f"[TeamOrchestrator] Failed to load state: {e}")
    
    def _save_state(self):
        """Persist orchestrator state"""
        state_file = self.data_dir / "orchestrator_state.json"
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    "task_history": self._task_history[-500:],
                    "custom_teams": [t.to_dict() for t in self._custom_teams.values()],
                    "last_saved": datetime.now().isoformat(),
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"[TeamOrchestrator] Failed to save state: {e}")
    
    # ==================== TEAM MANAGEMENT ====================
    
    def get_team(self, team_id: str) -> Optional[AgentTeam]:
        """Get a team by ID (preset or custom)"""
        return PRESET_TEAMS.get(team_id) or self._custom_teams.get(team_id)
    
    def list_teams(self, include_custom: bool = True) -> List[AgentTeam]:
        """List all available teams"""
        teams = list(PRESET_TEAMS.values())
        if include_custom:
            teams.extend(self._custom_teams.values())
        return teams
    
    def create_custom_team(
        self,
        id: str,
        name: str,
        description: str,
        members: List[str],
        leader: str,
        mode: TeamMode = TeamMode.SEQUENTIAL,
        emoji: str = "👥",
        **kwargs
    ) -> AgentTeam:
        """Create a custom team configuration"""
        team = AgentTeam(
            id=id,
            name=name,
            description=description,
            members=members,
            leader=leader,
            mode=mode,
            emoji=emoji,
            **kwargs
        )
        self._custom_teams[id] = team
        self._save_state()
        return team
    
    def delete_custom_team(self, team_id: str) -> bool:
        """Delete a custom team (cannot delete presets)"""
        if team_id in self._custom_teams:
            del self._custom_teams[team_id]
            self._save_state()
            return True
        return False
    
    # ==================== TASK ORCHESTRATION ====================
    
    def create_task(
        self,
        team_id: str,
        description: str,
        context: Dict[str, Any] = None,
        mode_override: TeamMode = None,
        dependencies: List[str] = None,
    ) -> TeamTask:
        """Create a new team task"""
        team = self.get_team(team_id)
        if not team:
            raise ValueError(f"Unknown team: {team_id}")
        
        task_id = f"team_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._task_history)}"
        
        task = TeamTask(
            id=task_id,
            description=description,
            team_id=team_id,
            mode=mode_override or team.mode,
            assigned_agents=team.members.copy(),
            context=context or {},
            dependencies=dependencies or [],
        )
        
        self._active_tasks[task_id] = task
        return task
    
    async def execute_task(self, task: TeamTask) -> Dict[str, Any]:
        """
        Execute a team task based on its mode.
        Returns aggregated results from all agents.
        """
        team = self.get_team(task.team_id)
        if not team:
            return {"error": f"Team not found: {task.team_id}"}
        
        task.status = TaskStatus.IN_PROGRESS
        
        try:
            # Check dependencies
            for dep_id in task.dependencies:
                dep_task = self._active_tasks.get(dep_id)
                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                    task.status = TaskStatus.BLOCKED
                    return {"error": f"Blocked by dependency: {dep_id}"}
            
            # Execute based on mode
            if task.mode == TeamMode.SEQUENTIAL:
                result = await self._execute_sequential(task, team)
            elif task.mode == TeamMode.PARALLEL:
                result = await self._execute_parallel(task, team)
            elif task.mode == TeamMode.CONSENSUS:
                result = await self._execute_consensus(task, team)
            elif task.mode == TeamMode.HIERARCHICAL:
                result = await self._execute_hierarchical(task, team)
            elif task.mode == TeamMode.ROUND_ROBIN:
                result = await self._execute_round_robin(task, team)
            else:
                result = {"error": f"Unknown mode: {task.mode}"}
            
            task.final_result = result
            task.status = TaskStatus.COMPLETED
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            result = {"error": str(e)}
            
            # Auto-escalate if configured
            if team.auto_escalate:
                await self._escalate_to_manager(task, str(e))
        
        # Archive task
        self._archive_task(task)
        
        return result
    
    async def _execute_sequential(self, task: TeamTask, team: AgentTeam) -> Dict[str, Any]:
        """Execute task sequentially - each agent builds on previous output"""
        from . import get_agent_instance
        
        accumulated_context = task.context.copy()
        results = {}
        
        for agent_id in task.assigned_agents:
            agent = get_agent_instance(agent_id)
            if not agent:
                results[agent_id] = {"error": f"Agent not found: {agent_id}"}
                continue
            
            # Build prompt with accumulated context
            prompt = f"""## Team Task: {task.description}

### Your Role
You are {agent.name} ({agent_id}), working as part of the {team.name} team.
Previous agents have contributed the following:
{json.dumps(accumulated_context, indent=2, default=str)}

### Instructions
1. Review the context from previous agents
2. Add your expertise and analysis
3. Build on their work, don't repeat it
4. Be specific about your domain ({agent_id})

Respond with your contribution."""
            
            try:
                response = await agent.chat(prompt)
                results[agent_id] = {
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                }
                accumulated_context[f"{agent_id}_contribution"] = response
                task.results[agent_id] = results[agent_id]
            except Exception as e:
                results[agent_id] = {"error": str(e)}
        
        return {
            "mode": "sequential",
            "team": team.id,
            "results": results,
            "final_context": accumulated_context,
        }
    
    async def _execute_parallel(self, task: TeamTask, team: AgentTeam) -> Dict[str, Any]:
        """Execute task in parallel - all agents work simultaneously"""
        from . import get_agent_instance
        
        async def run_agent(agent_id: str) -> tuple:
            agent = get_agent_instance(agent_id)
            if not agent:
                return agent_id, {"error": f"Agent not found: {agent_id}"}
            
            prompt = f"""## Team Task: {task.description}

### Your Role
You are {agent.name} ({agent_id}), working as part of the {team.name} team.
Context: {json.dumps(task.context, indent=2, default=str)}

### Instructions
Provide your analysis/response from your domain's perspective.
Focus on: {agent_id}
Be thorough but concise."""
            
            try:
                response = await agent.chat(prompt)
                return agent_id, {
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                }
            except Exception as e:
                return agent_id, {"error": str(e)}
        
        # Run all agents in parallel (with limit)
        semaphore = asyncio.Semaphore(team.max_parallel)
        
        async def limited_run(agent_id):
            async with semaphore:
                return await run_agent(agent_id)
        
        tasks = [limited_run(aid) for aid in task.assigned_agents]
        agent_results = await asyncio.gather(*tasks)
        
        results = dict(agent_results)
        task.results = results
        
        # Merge results
        merged = self._merge_parallel_results(results, task)
        
        return {
            "mode": "parallel",
            "team": team.id,
            "results": results,
            "merged": merged,
        }
    
    async def _execute_consensus(self, task: TeamTask, team: AgentTeam) -> Dict[str, Any]:
        """Execute task with consensus - agents vote on outcome"""
        from . import get_agent_instance
        
        # First, get all opinions in parallel
        parallel_result = await self._execute_parallel(task, team)
        
        # Then have each agent vote
        votes = {}
        for agent_id in task.assigned_agents:
            agent = get_agent_instance(agent_id)
            if not agent:
                continue
            
            vote_prompt = f"""## Consensus Vote

Task: {task.description}

All team members have provided input:
{json.dumps(parallel_result['results'], indent=2, default=str)}

Based on all inputs, what is your recommendation?
Reply with one of: APPROVE, REJECT, ABSTAIN
Then briefly explain why."""
            
            try:
                response = await agent.chat(vote_prompt)
                # Parse vote from response
                response_upper = response.upper()
                if "APPROVE" in response_upper:
                    vote = "APPROVE"
                elif "REJECT" in response_upper:
                    vote = "REJECT"
                else:
                    vote = "ABSTAIN"
                
                votes[agent_id] = {
                    "vote": vote,
                    "reasoning": response,
                }
            except Exception as e:
                votes[agent_id] = {"vote": "ABSTAIN", "error": str(e)}
        
        # Calculate consensus
        approve_count = sum(1 for v in votes.values() if v.get("vote") == "APPROVE")
        total_votes = len([v for v in votes.values() if v.get("vote") != "ABSTAIN"])
        
        if total_votes > 0:
            approval_ratio = approve_count / total_votes
            consensus_reached = approval_ratio >= team.require_consensus_threshold
        else:
            approval_ratio = 0
            consensus_reached = False
        
        return {
            "mode": "consensus",
            "team": team.id,
            "results": parallel_result["results"],
            "votes": votes,
            "approval_ratio": approval_ratio,
            "threshold": team.require_consensus_threshold,
            "consensus_reached": consensus_reached,
            "decision": "APPROVED" if consensus_reached else "REJECTED",
        }
    
    async def _execute_hierarchical(self, task: TeamTask, team: AgentTeam) -> Dict[str, Any]:
        """Execute task with hierarchical delegation"""
        from . import get_agent_instance
        
        leader = get_agent_instance(team.leader)
        if not leader:
            return {"error": f"Team leader not found: {team.leader}"}
        
        # Leader creates delegation plan
        delegate_prompt = f"""## Team Leadership Task

You are leading the {team.name} team.
Task: {task.description}
Context: {json.dumps(task.context, indent=2, default=str)}

Your team members are: {', '.join(task.assigned_agents)}

Create a delegation plan:
1. What should each team member focus on?
2. In what order should they work?
3. What are the success criteria?

Respond in JSON format:
{{
    "delegations": [
        {{"agent_id": "...", "focus": "...", "order": 1}},
        ...
    ],
    "success_criteria": "..."
}}"""
        
        try:
            plan_response = await leader.chat(delegate_prompt)
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', plan_response)
            if json_match:
                plan = json.loads(json_match.group())
            else:
                # Fallback: simple sequential delegation
                plan = {
                    "delegations": [
                        {"agent_id": aid, "focus": task.description, "order": i}
                        for i, aid in enumerate(task.assigned_agents) if aid != team.leader
                    ],
                    "success_criteria": "All agents complete their assigned tasks"
                }
        except Exception:
            plan = {
                "delegations": [
                    {"agent_id": aid, "focus": task.description, "order": i}
                    for i, aid in enumerate(task.assigned_agents) if aid != team.leader
                ],
                "success_criteria": "All agents complete their assigned tasks"
            }
        
        # Execute delegations
        results = {"leader_plan": plan}
        delegations = sorted(plan.get("delegations", []), key=lambda x: x.get("order", 0))
        
        for delegation in delegations:
            agent_id = delegation.get("agent_id")
            focus = delegation.get("focus", task.description)
            
            agent = get_agent_instance(agent_id)
            if not agent:
                results[agent_id] = {"error": f"Agent not found"}
                continue
            
            agent_prompt = f"""## Delegated Task from {leader.name}

Main task: {task.description}
Your specific focus: {focus}

Complete your assigned portion and report back."""
            
            try:
                response = await agent.chat(agent_prompt)
                results[agent_id] = {
                    "focus": focus,
                    "response": response,
                }
                task.results[agent_id] = results[agent_id]
            except Exception as e:
                results[agent_id] = {"error": str(e)}
        
        # Leader reviews results
        review_prompt = f"""## Review Team Results

You delegated the following task: {task.description}

Team results:
{json.dumps(results, indent=2, default=str)}

Provide a summary of:
1. What was accomplished
2. Any issues or gaps
3. Final recommendation"""
        
        try:
            review = await leader.chat(review_prompt)
            results["leader_review"] = review
        except Exception as e:
            results["leader_review"] = {"error": str(e)}
        
        return {
            "mode": "hierarchical",
            "team": team.id,
            "leader": team.leader,
            "plan": plan,
            "results": results,
        }
    
    async def _execute_round_robin(self, task: TeamTask, team: AgentTeam) -> Dict[str, Any]:
        """Execute with round-robin task distribution"""
        # For round-robin, we just do parallel since each agent handles their slice
        return await self._execute_parallel(task, team)
    
    def _merge_parallel_results(self, results: Dict[str, Any], task: TeamTask) -> str:
        """Merge results from parallel execution into a summary"""
        summaries = []
        for agent_id, result in results.items():
            if "error" in result:
                summaries.append(f"**{agent_id}**: ❌ Error - {result['error']}")
            elif "response" in result:
                # Truncate long responses
                response = result["response"]
                if len(response) > 500:
                    response = response[:500] + "..."
                summaries.append(f"**{agent_id}**: {response}")
        
        return "\n\n".join(summaries)
    
    async def _escalate_to_manager(self, task: TeamTask, error: str):
        """Escalate failed task to manager"""
        from .coordination import get_coordinator
        coordinator = get_coordinator()
        
        coordinator.send_message(
            from_agent="team_orchestrator",
            to_agent="manager",
            message_type="task_escalation",
            content={
                "task_id": task.id,
                "team_id": task.team_id,
                "description": task.description,
                "error": error,
                "partial_results": task.results,
            },
            priority="high"
        )
    
    def _archive_task(self, task: TeamTask):
        """Archive a completed/failed task"""
        if task.id in self._active_tasks:
            del self._active_tasks[task.id]
        
        self._task_history.append(task.to_dict())
        self._save_state()
    
    # ==================== QUERIES ====================
    
    def get_active_tasks(self) -> List[TeamTask]:
        """Get all active team tasks"""
        return list(self._active_tasks.values())
    
    def get_task(self, task_id: str) -> Optional[TeamTask]:
        """Get a specific task"""
        return self._active_tasks.get(task_id)
    
    def get_task_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent task history"""
        return self._task_history[-limit:][::-1]
    
    def get_team_stats(self, team_id: str) -> Dict[str, Any]:
        """Get statistics for a team"""
        team_tasks = [t for t in self._task_history if t.get("team_id") == team_id]
        
        completed = sum(1 for t in team_tasks if t.get("status") == TaskStatus.COMPLETED.value)
        failed = sum(1 for t in team_tasks if t.get("status") == TaskStatus.FAILED.value)
        
        return {
            "team_id": team_id,
            "total_tasks": len(team_tasks),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / len(team_tasks) if team_tasks else 0,
        }


# Helper function to get agent instances
def get_agent_instance(agent_id: str):
    """Get an agent instance by ID"""
    from . import (
        FinanceAgent, MaintenanceAgent, ContractorsAgent,
        ProjectsAgent, SecurityManagerAgent, JanitorAgent, ManagerAgent
    )
    
    agent_classes = {
        "finance": FinanceAgent,
        "maintenance": MaintenanceAgent,
        "contractors": ContractorsAgent,
        "projects": ProjectsAgent,
        "security": SecurityManagerAgent,
        "janitor": JanitorAgent,
        "manager": ManagerAgent,
    }
    
    cls = agent_classes.get(agent_id)
    if cls:
        return cls()
    return None


# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> TeamOrchestrator:
    """Get or create the global team orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TeamOrchestrator()
    return _orchestrator
