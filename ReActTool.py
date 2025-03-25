import os
import json
import httpx
import logging
import asyncio
import uuid
import re
from typing import Any, Dict, Optional
from tools import TOOL_CONFIG
from mcp.server.fastmcp import FastMCP

# Set up basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize the MCP server (the name "vc" must match your configuration)
mcp = FastMCP("vc")

# Global in-memory job store for async operations.
jobs: Dict[str, Dict[str, Any]] = {}

# Load API key from environment or use a default (replace with your key)
API_KEY = os.getenv("WORDWARE_API_KEY")

def render_template(template: Any, context: Dict[str, Any]) -> Any:
    """
    Recursively renders a template (string, dict, or list) using Python's str.format.
    The template should use placeholders like "{title}".
    """
    if isinstance(template, str):
        try:
            return template.format(**context)
        except KeyError as e:
            logger.error(f"Missing key in context for template: {e}")
            return template
    elif isinstance(template, dict):
        return {k: render_template(v, context) for k, v in template.items()}
    elif isinstance(template, list):
        return [render_template(item, context) for item in template]
    else:
        return template

class DynamicWordwareTool:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the dynamic tool with the given configuration.
        
        Expected config keys:
          - description: Brief description of what the tool does.
          - payload_template: A dict acting as a payload template 
                              (e.g. {"inputs": {"title": "{title}", "body": "{body}"}, "version": "^1.0"}).
          - api_url: The Wordware API endpoint URL.
          - async: Boolean indicating whether to use async execution.
        """
        self.description = config.get("description", "No description provided")
        self.payload_template = config.get("payload_template", {})
        self.api_url = config.get("api_url")
        self.use_async = config.get("async", True)
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        logger.info(f"Initialized tool with API URL: {self.api_url}")
        logger.info(f"Payload template: {self.payload_template}")
    
    def render_payload(self, **kwargs) -> Dict[str, Any]:
        """Render the payload by substituting placeholders with actual values."""
        try:
            rendered = render_template(self.payload_template, kwargs)
            logger.info(f"Rendered payload template with kwargs {kwargs}: {rendered}")
            return rendered
        except Exception as e:
            logger.error(f"Error rendering payload: {e}")
            raise
    
    async def call_api(self, payload: Dict[str, Any]) -> str:
        """Call the Wordware API and process its streaming response."""
        logger.info(f"Calling API {self.api_url}")
        logger.info(f"Headers: {self.headers}")
        logger.info(f"Payload: {payload}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {response.headers}")
                logger.info(f"Response text: {response.text}")
                
                if response.status_code != 200:
                    error_msg = f"API call failed with status {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return error_msg
                    
                return self.process_response(response.text)
        except Exception as e:
            error_msg = f"API call failed with error: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def process_response(self, response_text: str) -> str:
        """
        Process a streaming response and extract the desired output.
        Assumes a line exists in the response with a JSON chunk like:
            { "type": "chunk", "value": {"type": "code", "output": "..." } }
        """
        logger.info(f"Processing response text: {response_text}")
        for line in response_text.split('\n'):
            if line.strip():
                try:
                    chunk = json.loads(line)
                    logger.info(f"Processing chunk: {chunk}")
                    if (chunk.get("type") == "chunk" and 
                        chunk.get("value", {}).get("type") == "code" and 
                        chunk.get("value", {}).get("output")):
                        result = chunk["value"]["output"]
                        logger.info(f"Found result: {result}")
                        return result
                except json.JSONDecodeError:
                    continue
        return "No output found"
    
    async def run(self, **kwargs) -> str:
        """Run the tool synchronously (i.e. wait for the API response immediately)."""
        try:
            logger.info(f"Running tool with kwargs: {kwargs}")
            payload = self.render_payload(**kwargs)
            result = await self.call_api(payload)
            logger.info(f"Tool run completed with result: {result}")
            return result
        except Exception as e:
            error_msg = f"Tool run failed: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def run_async(self, **kwargs) -> Dict[str, Any]:
        """
        Run the tool asynchronously.
        This method immediately returns a job ID while the task runs in the background.
        """
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "pending", "result": None, "error": None}
        asyncio.create_task(self._background_run(job_id, **kwargs))
        return {"job_id": job_id, "status": "pending"}
    
    async def _background_run(self, job_id: str, **kwargs):
        """Background task to run the API call and update the job store."""
        try:
            jobs[job_id]["status"] = "processing"
            payload = self.render_payload(**kwargs)
            result = await self.call_api(payload)
            jobs[job_id]["status"] = "complete"
            jobs[job_id]["result"] = result
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)


# Dynamically create tools based on the configuration.
dynamic_tools: Dict[str, DynamicWordwareTool] = {}
for tool_name, config in TOOL_CONFIG.items():
    dynamic_tools[tool_name] = DynamicWordwareTool(config)

async def get_dynamic_job_status(job_id: str) -> Dict[str, Any]:
    """Poll for the status of an asynchronous job."""
    if job_id not in jobs:
        return {"error": "Invalid job ID"}
    return jobs[job_id]

async def react_agent(user_command: str, title: str, body: str, initial_result: Optional[str] = None) -> str:
    """
    A ReAct-style agent that:
      1. Receives the user command and the initial result from the Wordware tool.
      2. Simulates a chain-of-thought process.
      3. Decides if additional multi-step processing is required.
      4. If so, chains further steps (e.g. refining the result).
    
    Returns the final result.
    """
    print("ReAct Agent: Received command:", user_command)
    if initial_result:
        print("ReAct Agent: Initial tool result:", initial_result)
    
    # Simulated chain-of-thought process.
    thoughts = [
        "A matching Wordware tool was used.",
        "Reviewing the initial output to decide if further processing is needed."
    ]
    for thought in thoughts:
        print("ReAct Agent:", thought)
        await asyncio.sleep(0.5)
    
    # For this example, if the command contains "multi-step" or the body is very long,
    # assume that further processing is required.
    if "multi-step" in user_command.lower() or len(body) > 100:
        print("ReAct Agent: Additional processing required. Executing further steps...")
        additional_info = " [Finalized after multi-step processing]"
        final_result = (initial_result or "") + additional_info
        print("ReAct Agent: Final result after additional processing:", final_result)
        return final_result
    else:
        print("ReAct Agent: No further processing needed. Returning the initial result.")
        return initial_result or "No result from tool."

@mcp.tool()
async def handle_user_request(user_command: str, tool: str, **inputs) -> str:
    """
    Entry point for user requests.

    For multi-step reasoning (e.g., use the output of one tool as input to another), Claude should call this tool first and describe the desired outcome clearly in the `user_command`.

    If a task requires multiple steps, this tool will internally invoke a ReAct-style agent to orchestrate the steps.

    This is a tool that is used to handle user requests. 
    Here are a list of tools available:
    - notion_page (use to create a new page in Notion)
    - google_search (use to search the web to get up to date information or current information)
    - wikipedia_lookup (use to get information from wikipedia, if you need to know more about a topic or need to research something)
    - google_news (use to get the latest news)
    
    When the tool is called, Claude tells it which tool it wants to use.
    The process is as follows:
      1. Use the provided tool (e.g., "notion_page") to handle the request.
      2. Call the chosen tool to get an initial result.
      3. If the query indicates multi-step processing is needed (e.g., contains "multi-step"),
         delegate to the ReAct agent for further processing.
    """
    print("handle_user_request: Received user command:", user_command)
    print(f"handle_user_request: Claude selected tool '{tool}'")
    print(f"handle_user_request: Raw inputs: {inputs}")

    if tool not in dynamic_tools:
        return f"Tool '{tool}' not available."

    selected_tool = dynamic_tools[tool]

    processed_inputs = {}
    # Process inputs based on tool type
    if tool in ["google_search", "wikipedia_lookup"]:
        # For search tools, combine all inputs into a query
        query_parts = []
        for key, value in inputs.items():
            if value:
                query_parts.append(str(value))
        processed_inputs["query"] = " ".join(query_parts)
    elif tool == "google_news":
        # For news search, combine all inputs into a news query
        news_parts = []
        for key, value in inputs.items():
            if value and key not in ["user_command", "tool"]:
                news_parts.append(str(value))
        processed_inputs["news"] = " ".join(news_parts)
        logger.info(f"Google News query: {processed_inputs['news']}")
    elif tool == "notion_page":
        # For Notion, extract title and body
        processed_inputs["title"] = inputs.get("inputs").get("title", "example title")
        processed_inputs["body"] = inputs.get("inputs").get("body", "example body")
    else:
        # For other tools, pass inputs as-is
        processed_inputs = inputs
    
  

    logger.info(f"the original inputs: {inputs}")
    logger.info(f"Processed inputs: {processed_inputs}")
    print(f"handle_user_request: Running tool with processed inputs: {processed_inputs}")
    initial_result = await selected_tool.run(**processed_inputs)

    if "multi-step" in user_command.lower():
        print("handle_user_request: Delegating to ReAct agent for additional processing...")
        final_result = await react_agent(user_command, **processed_inputs, initial_result=initial_result)
        return final_result
    else:
        print("handle_user_request: Returning initial result without additional processing.")
        return initial_result

if __name__ == "__main__":
    mcp.run(transport='stdio')