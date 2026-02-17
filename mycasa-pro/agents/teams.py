"""
MyCasa Pro - Agent Teams
========================

Pre-configured agent groups for coordinated multi-agent tasks.
Inspired by LobeHub's "Agent Groups" feature.

Teams enable:
- Parallel collaboration on single tasks
- Coordinated decision-making
- Iterative improvement between agents
- Clear accountability and ownership

Usage:
    from agents.teams import TEAMS, TeamRouter
    
    router = TeamRouter()
    result = await router.delegate_to_team("finance_review", task, context)
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from core.secondbrain.models import AgentType


class TeamType(str, Enum):
    """Available team types"""
    FINANCE_REVIEW = "finance_review"
    MAINTENANCE_DISPATCH = "maintenance_dispatch"
    SECURITY_RESPONSE = "security_response"
    PROJECT_PLANNING = "project_planning"
    DAILY_OPERATIONS = "daily_operations"


@dataclass
class TeamConfig:
    """Configuration for an agent team"""
    name: str
    members: List[AgentType]
    leader: AgentType
    purpose: str
    collaboration_mode: str = "parallel"  # parallel, sequential, consensus
    max_iterations: int = 3
    require_consensus: bool = False
    
    def __post_init__(self):
        # Validate leader is a member
        if self.leader not in self.members:
            self.members.append(self.leader)


# Pre-configured teams
TEAMS: Dict[TeamType, TeamConfig] = {
    TeamType.FINANCE_REVIEW: TeamConfig(
        name="Finance Review Team",
        members=[AgentType.FINANCE, AgentType.JANITOR],
        leader=AgentType.MANAGER,
        purpose="Review and validate financial transactions, budgets, and spending",
        collaboration_mode="sequential",
        require_consensus=True,
    ),
    
    TeamType.MAINTENANCE_DISPATCH: TeamConfig(
        name="Maintenance Dispatch Team",
        members=[AgentType.MAINTENANCE, AgentType.CONTRACTORS],
        leader=AgentType.MANAGER,
        purpose="Handle maintenance requests and contractor coordination",
        collaboration_mode="parallel",
    ),
    
    TeamType.SECURITY_RESPONSE: TeamConfig(
        name="Security Response Team",
        members=[AgentType.SECURITY, AgentType.MAINTENANCE],
        leader=AgentType.MANAGER,
        purpose="Handle security incidents and emergency responses",
        collaboration_mode="parallel",
        max_iterations=1,  # Fast response needed
    ),
    
    TeamType.PROJECT_PLANNING: TeamConfig(
        name="Project Planning Team",
        members=[AgentType.PROJECTS, AgentType.CONTRACTORS, AgentType.FINANCE],
        leader=AgentType.MANAGER,
        purpose="Plan and estimate home improvement projects",
        collaboration_mode="sequential",
        require_consensus=True,
    ),
    
    TeamType.DAILY_OPERATIONS: TeamConfig(
        name="Daily Operations Team",
        members=[AgentType.MAINTENANCE, AgentType.FINANCE, AgentType.JANITOR],
        leader=AgentType.MANAGER,
        purpose="Handle routine daily household operations",
        collaboration_mode="parallel",
    ),
}


@dataclass
class TeamMemberResult:
    """Result from a single team member"""
    agent: AgentType
    response: str
    confidence: float
    reasoning: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class TeamResult:
    """Aggregated result from team collaboration"""
    team: TeamType
    task: str
    member_results: List[TeamMemberResult]
    synthesis: str
    consensus_reached: bool = True
    iterations: int = 1
    reasoning_log: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "team": self.team.value,
            "task": self.task[:100],
            "member_count": len(self.member_results),
            "synthesis": self.synthesis,
            "consensus_reached": self.consensus_reached,
            "iterations": self.iterations,
            "reasoning_log": self.reasoning_log,
        }


class TeamRouter:
    """
    Routes tasks to agent teams and coordinates collaboration.
    
    Collaboration modes:
    - parallel: All members work simultaneously, leader synthesizes
    - sequential: Members work in order, each builds on previous
    - consensus: All must agree, iterate until consensus
    """
    
    def __init__(self, manager_agent=None):
        self.manager = manager_agent
        self._reasoning_log: List[str] = []
    
    def _log(self, message: str):
        self._reasoning_log.append(message)
    
    def get_team(self, team_type: TeamType) -> TeamConfig:
        """Get team configuration"""
        return TEAMS[team_type]
    
    def suggest_team(self, task: str) -> Optional[TeamType]:
        """
        Suggest the best team for a task based on keywords.
        Returns None if no specific team matches.
        """
        task_lower = task.lower()
        
        # Finance-related
        if any(kw in task_lower for kw in ["budget", "expense", "cost", "payment", "bill", "money", "spend"]):
            return TeamType.FINANCE_REVIEW
        
        # Maintenance-related
        if any(kw in task_lower for kw in ["repair", "fix", "broken", "maintenance", "plumber", "electrician", "leak", "leaking", "clog", "hvac", "appliance"]):
            return TeamType.MAINTENANCE_DISPATCH
        
        # Security-related
        if any(kw in task_lower for kw in ["security", "alarm", "camera", "intrusion", "emergency", "threat", "motion", "detected", "alert", "suspicious"]):
            return TeamType.SECURITY_RESPONSE
        
        # Project-related
        if any(kw in task_lower for kw in ["project", "renovation", "remodel", "install", "upgrade", "plan"]):
            return TeamType.PROJECT_PLANNING
        
        return None
    
    async def delegate_to_team(
        self,
        team_type: TeamType,
        task: str,
        context: Dict[str, Any],
    ) -> TeamResult:
        """
        Delegate a task to a team and coordinate collaboration.
        
        Args:
            team_type: Which team to use
            task: The task description
            context: Shared context for all agents
            
        Returns:
            TeamResult with aggregated responses and synthesis
        """
        team = TEAMS[team_type]
        self._reasoning_log = []
        
        self._log(f"Team activated: {team.name}")
        self._log(f"Members: {[m.value for m in team.members]}")
        self._log(f"Mode: {team.collaboration_mode}")
        
        if team.collaboration_mode == "parallel":
            result = await self._parallel_collaboration(team, task, context)
        elif team.collaboration_mode == "sequential":
            result = await self._sequential_collaboration(team, task, context)
        elif team.collaboration_mode == "consensus":
            result = await self._consensus_collaboration(team, task, context)
        else:
            result = await self._parallel_collaboration(team, task, context)
        
        result.reasoning_log = self._reasoning_log
        return result
    
    async def _parallel_collaboration(
        self,
        team: TeamConfig,
        task: str,
        context: Dict[str, Any],
    ) -> TeamResult:
        """All team members work simultaneously"""
        import asyncio
        
        self._log("Starting parallel execution...")
        
        # Get results from all members (except leader)
        members = [m for m in team.members if m != team.leader]
        
        async def get_member_result(agent_type: AgentType) -> TeamMemberResult:
            try:
                if self.manager:
                    response = await self.manager._delegate_to_specialist(
                        agent_type, task, context
                    )
                    return TeamMemberResult(
                        agent=agent_type,
                        response=response.content if hasattr(response, 'content') else str(response),
                        confidence=response.confidence if hasattr(response, 'confidence') else 0.8,
                        reasoning=response.reasoning_log if hasattr(response, 'reasoning_log') else [],
                    )
                else:
                    # Stub for testing without manager
                    return TeamMemberResult(
                        agent=agent_type,
                        response=f"[{agent_type.value}] Analysis of: {task[:50]}",
                        confidence=0.8,
                    )
            except Exception as e:
                return TeamMemberResult(
                    agent=agent_type,
                    response=f"Error: {e}",
                    confidence=0.0,
                )
        
        # Execute in parallel
        member_results = await asyncio.gather(
            *[get_member_result(m) for m in members]
        )
        
        self._log(f"Received {len(member_results)} member responses")
        
        # Leader synthesizes
        synthesis = await self._synthesize(team.leader, task, list(member_results), context)
        
        return TeamResult(
            team=TeamType(team.name.lower().replace(" ", "_").replace("team", "").strip("_")),
            task=task,
            member_results=list(member_results),
            synthesis=synthesis,
        )
    
    async def _sequential_collaboration(
        self,
        team: TeamConfig,
        task: str,
        context: Dict[str, Any],
    ) -> TeamResult:
        """Members work in sequence, building on each other"""
        self._log("Starting sequential execution...")
        
        members = [m for m in team.members if m != team.leader]
        member_results = []
        accumulated_context = dict(context)
        
        for i, agent_type in enumerate(members):
            self._log(f"Step {i+1}: {agent_type.value}")
            
            # Add previous results to context
            if member_results:
                accumulated_context["previous_results"] = [
                    {"agent": r.agent.value, "response": r.response}
                    for r in member_results
                ]
            
            try:
                if self.manager:
                    response = await self.manager._delegate_to_specialist(
                        agent_type, task, accumulated_context
                    )
                    result = TeamMemberResult(
                        agent=agent_type,
                        response=response.content if hasattr(response, 'content') else str(response),
                        confidence=response.confidence if hasattr(response, 'confidence') else 0.8,
                    )
                else:
                    result = TeamMemberResult(
                        agent=agent_type,
                        response=f"[{agent_type.value}] Sequential analysis of: {task[:50]}",
                        confidence=0.8,
                    )
                member_results.append(result)
            except Exception as e:
                member_results.append(TeamMemberResult(
                    agent=agent_type,
                    response=f"Error: {e}",
                    confidence=0.0,
                ))
        
        self._log(f"Completed {len(member_results)} sequential steps")
        
        # Leader synthesizes
        synthesis = await self._synthesize(team.leader, task, member_results, context)
        
        return TeamResult(
            team=TeamType(team.name.lower().replace(" ", "_").replace("team", "").strip("_")),
            task=task,
            member_results=member_results,
            synthesis=synthesis,
        )
    
    async def _consensus_collaboration(
        self,
        team: TeamConfig,
        task: str,
        context: Dict[str, Any],
    ) -> TeamResult:
        """Iterate until all members agree"""
        self._log("Starting consensus-building...")
        
        iteration = 0
        consensus_reached = False
        member_results = []
        
        while iteration < team.max_iterations and not consensus_reached:
            iteration += 1
            self._log(f"Iteration {iteration}/{team.max_iterations}")
            
            # Get parallel results
            result = await self._parallel_collaboration(team, task, context)
            member_results = result.member_results
            
            # Check for consensus (simplified: all confidence > 0.7)
            confidences = [r.confidence for r in member_results]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            if avg_confidence >= 0.7:
                consensus_reached = True
                self._log(f"Consensus reached at iteration {iteration}")
            else:
                self._log(f"No consensus (avg confidence: {avg_confidence:.2f})")
                # Add disagreement to context for next iteration
                context["previous_attempt"] = {
                    "iteration": iteration,
                    "results": [r.response for r in member_results],
                }
        
        synthesis = await self._synthesize(team.leader, task, member_results, context)
        
        return TeamResult(
            team=TeamType(team.name.lower().replace(" ", "_").replace("team", "").strip("_")),
            task=task,
            member_results=member_results,
            synthesis=synthesis,
            consensus_reached=consensus_reached,
            iterations=iteration,
        )
    
    async def _synthesize(
        self,
        leader: AgentType,
        task: str,
        results: List[TeamMemberResult],
        context: Dict[str, Any],
    ) -> str:
        """Leader synthesizes member results into final response"""
        self._log(f"Leader ({leader.value}) synthesizing {len(results)} results")
        
        # Build synthesis prompt
        results_summary = "\n".join([
            f"- {r.agent.value}: {r.response[:200]}..." if len(r.response) > 200 else f"- {r.agent.value}: {r.response}"
            for r in results
        ])
        
        synthesis_task = f"""Synthesize these team member responses for the task: {task}

Member Responses:
{results_summary}

Provide a unified response that incorporates the best insights from each member."""
        
        if self.manager:
            response = await self.manager._delegate_to_specialist(
                leader, synthesis_task, context
            )
            return response.content if hasattr(response, 'content') else str(response)
        else:
            # Stub for testing
            return f"[Synthesis] Combined analysis from {len(results)} team members for: {task[:50]}"


def get_team_for_task(task: str) -> Optional[TeamType]:
    """Helper to suggest a team for a given task"""
    router = TeamRouter()
    return router.suggest_team(task)


def list_teams() -> Dict[str, Dict[str, Any]]:
    """List all available teams with their configurations"""
    return {
        team_type.value: {
            "name": config.name,
            "members": [m.value for m in config.members],
            "leader": config.leader.value,
            "purpose": config.purpose,
            "mode": config.collaboration_mode,
        }
        for team_type, config in TEAMS.items()
    }
