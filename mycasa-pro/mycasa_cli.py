#!/usr/bin/env python3
"""
MyCasa Pro CLI - Agent interface for claude-flow integration
"""
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def get_agent(agent_name: str):
    """Get an agent instance by name"""
    if agent_name == "manager":
        from agents.manager import ManagerAgent
        return ManagerAgent()
    elif agent_name == "janitor":
        from agents.janitor import JanitorAgent
        return JanitorAgent()
    elif agent_name == "finance":
        from agents.finance import FinanceAgent
        return FinanceAgent()
    elif agent_name == "maintenance":
        from agents.maintenance import MaintenanceAgent
        return MaintenanceAgent()
    elif agent_name == "contractors":
        from agents.contractors import ContractorsAgent
        return ContractorsAgent()
    elif agent_name == "projects":
        from agents.projects import ProjectsAgent
        return ProjectsAgent()
    else:
        raise ValueError(f"Unknown agent: {agent_name}")


def main():
    parser = argparse.ArgumentParser(description="MyCasa Pro Agent CLI")
    parser.add_argument("agent", help="Agent name (manager, janitor, finance, maintenance, contractors, projects)")
    parser.add_argument("command", help="Command to execute")
    parser.add_argument("--args", "-a", help="JSON arguments", default="{}")
    parser.add_argument("--pretty", "-p", action="store_true", help="Pretty print output")
    
    args = parser.parse_args()
    
    try:
        agent = get_agent(args.agent)
        cmd_args = json.loads(args.args)
        
        # Get the method
        if not hasattr(agent, args.command):
            print(json.dumps({"error": f"Unknown command: {args.command}"}))
            sys.exit(1)
        
        method = getattr(agent, args.command)
        
        # Call the method
        if callable(method):
            if cmd_args:
                result = method(**cmd_args)
            else:
                result = method()
        else:
            result = method  # It's a property
        
        # Output
        indent = 2 if args.pretty else None
        print(json.dumps(result, default=str, indent=indent))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
