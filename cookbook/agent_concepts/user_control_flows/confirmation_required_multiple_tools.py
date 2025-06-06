"""🤝 Human-in-the-Loop: Adding User Confirmation to Tool Calls

This example shows how to implement human-in-the-loop functionality in your Agno tools.
It shows how to:
- Handle user confirmation during tool execution
- Gracefully cancel operations based on user choice

Some practical applications:
- Confirming sensitive operations before execution
- Reviewing API calls before they're made
- Validating data transformations
- Approving automated actions in critical systems

Run `pip install openai httpx rich agno` to install dependencies.
"""

import json

import httpx
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import tool
from agno.tools.wikipedia import WikipediaTools
from agno.utils import pprint
from rich.console import Console
from rich.prompt import Prompt

console = Console()


@tool(requires_confirmation=True)
def get_top_hackernews_stories(num_stories: int) -> str:
    """Fetch top stories from Hacker News.

    Args:
        num_stories (int): Number of stories to retrieve

    Returns:
        str: JSON string containing story details
    """
    # Fetch top story IDs
    response = httpx.get("https://hacker-news.firebaseio.com/v0/topstories.json")
    story_ids = response.json()

    # Yield story details
    all_stories = []
    for story_id in story_ids[:num_stories]:
        story_response = httpx.get(
            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        )
        story = story_response.json()
        if "text" in story:
            story.pop("text", None)
        all_stories.append(story)
    return json.dumps(all_stories)


agent = Agent(
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[
        get_top_hackernews_stories,
        WikipediaTools(requires_confirmation_tools=["search_wikipedia"]),
    ],
    markdown=True,
    debug_mode=True,
)

run_response = agent.run(
    "Fetch 2 articles about the topic 'python'. You can choose which source to use, but only use one source."
)
while run_response.is_paused:  # Or agent.run_response.is_paused
    for tool in agent.run_response.tools_requiring_confirmation:
        # Ask for confirmation
        console.print(
            f"Tool name [bold blue]{tool.tool_name}({tool.tool_args})[/] requires confirmation."
        )
        message = (
            Prompt.ask("Do you want to continue?", choices=["y", "n"], default="y")
            .strip()
            .lower()
        )

        if message == "n":
            tool.confirmed = False
            tool.confirmation_note = (
                "This is not the right tool to use. Use the other tool!"
            )
        else:
            # We update the tools in place
            tool.confirmed = True

    run_response = agent.continue_run()
