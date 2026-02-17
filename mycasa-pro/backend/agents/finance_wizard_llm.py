"""
LLM-Powered Portfolio Wizard Prompts
Generates dynamic prompts for the portfolio wizard using Claude.
"""
import asyncio
from typing import Dict, Any, List


async def generate_wizard_prompt(
    step: str,
    context: Dict[str, Any],
    llm_client
) -> str:
    """
    Generate a wizard prompt using LLM based on step and context.

    Args:
        step: Current wizard step (menu, add_ticker, add_shares, etc.)
        context: Context data (holdings, ticker, shares, etc.)
        llm_client: LLM client instance

    Returns:
        Generated prompt text in Mamadou's voice
    """

    if not llm_client or not llm_client.is_available():
        # Fallback to basic template if LLM unavailable
        return _fallback_prompt(step, context)

    # Build system prompt for wizard interactions
    system_prompt = """You are Mamadou (💰), the Finance Agent for MyCasa Pro.

Your personality:
- Professional but friendly
- Clear and concise
- Use numbered options for choices
- End prompts with "— Mamadou 💰"
- Use emojis sparingly but effectively

You're guiding the user through the portfolio wizard. Generate natural, helpful prompts that:
1. Clearly state what step they're on
2. Show relevant context (current data)
3. Explain what input is expected
4. Use formatting (bold for important info, bullets for lists)

Keep responses under 150 words. Be conversational but efficient."""

    # Build user message based on step
    user_message = _build_step_message(step, context)

    try:
        response = await llm_client.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=400,
            temperature=0.7  # Slightly creative but consistent
        )
        return response
    except Exception as e:
        # Fallback on error
        return _fallback_prompt(step, context)


def _build_step_message(step: str, context: Dict[str, Any]) -> str:
    """Build the prompt generation message based on step"""

    if step == "menu":
        holdings_count = context.get("holdings_count", 0)
        return f"""Generate a portfolio wizard main menu.
Current state: {holdings_count} holdings in portfolio.

Options to show:
1. Add a new holding
2. Edit existing holding
3. Remove a holding
4. View portfolio
5. Clear all holdings
0. Exit wizard

Make it welcoming and clear. Include a header with "PORTFOLIO WIZARD" and the holdings count."""

    elif step == "add_ticker":
        return """Generate a prompt asking for ticker symbol.
This is step 1/3 of adding a holding.
Ask for the ticker symbol (e.g., AAPL, GOOGL).
Make it clear and simple."""

    elif step == "add_shares":
        ticker = context.get("ticker", "???")
        return f"""Generate a prompt asking for number of shares.
This is step 2/3 of adding a holding.
Ticker: {ticker}
Ask how many shares they want to add."""

    elif step == "add_type":
        ticker = context.get("ticker", "???")
        shares = context.get("shares", 0)
        return f"""Generate a prompt asking for asset type.
This is step 3/3 of adding a holding.
Ticker: {ticker}
Shares: {shares:,.2f}

Asset type options:
1. Stock
2. ETF
3. Tech
4. Crypto/BTC
5. Gold
6. Dividend
7. Other

Ask them to choose a number 1-7."""

    elif step == "edit_select":
        holdings = context.get("holdings", [])
        if not holdings:
            return "Generate a message saying portfolio is empty and they should add holdings first. Then show them back to the menu."

        holdings_list = "\n".join([
            f"{i+1}. {h['ticker']}: {h['shares']:,.2f} shares ({h['type']})"
            for i, h in enumerate(holdings)
        ])
        return f"""Generate a prompt for editing a holding.
Show these holdings as numbered options:
{holdings_list}

Include option 0 to go back to menu.
Ask them to select a number."""

    elif step == "edit_shares":
        ticker = context.get("ticker", "???")
        current_shares = context.get("current_shares", 0)
        return f"""Generate a prompt for editing shares.
Editing: {ticker}
Current shares: {current_shares:,.2f}
Ask for the new number of shares."""

    elif step == "remove_select":
        holdings = context.get("holdings", [])
        if not holdings:
            return "Generate a message saying portfolio is empty."

        holdings_list = "\n".join([
            f"{i+1}. {h['ticker']}: {h['shares']:,.2f} shares"
            for i, h in enumerate(holdings)
        ])
        return f"""Generate a prompt for removing a holding.
Show these holdings as numbered options:
{holdings_list}

Include option 0 to go back.
Ask which one to remove."""

    elif step == "confirm_remove":
        ticker = context.get("ticker", "???")
        shares = context.get("shares", 0)
        return f"""Generate a confirmation prompt for removal.
Removing: {ticker} ({shares:,.2f} shares)
Ask for yes/no confirmation. Make it clear this will remove the holding."""

    elif step == "confirm_clear":
        count = context.get("count", 0)
        return f"""Generate a confirmation prompt for clearing all holdings.
Total holdings: {count}
This will delete ALL holdings. Ask for yes/no confirmation. Emphasize this cannot be undone."""

    elif step == "view":
        holdings = context.get("holdings", [])
        if not holdings:
            return "Generate a message showing empty portfolio. Suggest adding holdings (option 1) or exiting (option 0)."

        holdings_list = "\n".join([
            f"• {h['ticker']}: {h['shares']:,.2f} shares ({h['type']})"
            for h in holdings
        ])
        total_shares = sum(h['shares'] for h in holdings)

        return f"""Generate a portfolio summary view.
Holdings:
{holdings_list}

Total: {len(holdings)} positions, {total_shares:,.2f} shares

Show this nicely formatted. Tell them to reply 0 to go back to menu."""

    else:
        return f"Generate a prompt for step: {step}"


def _fallback_prompt(step: str, context: Dict[str, Any]) -> str:
    """Simple fallback prompts if LLM unavailable"""

    if step == "menu":
        holdings_count = context.get("holdings_count", 0)
        return f"""💰 **PORTFOLIO WIZARD** ({holdings_count} positions)

1. Add holding
2. Edit holding
3. Remove holding
4. View portfolio
5. Clear all
0. Exit

— Mamadou 💰"""

    elif step == "add_ticker":
        return """📈 **ADD HOLDING** (1/3)

Enter ticker symbol (e.g., AAPL):

— Mamadou 💰"""

    elif step == "add_shares":
        ticker = context.get("ticker", "???")
        return f"""📈 **ADD HOLDING** (2/3)

Ticker: **{ticker}**
Enter number of shares:

— Mamadou 💰"""

    # Add more fallbacks as needed
    return f"[Step: {step}] — Mamadou 💰"
