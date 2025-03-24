import os
import json
import httpx
import logging
import re
import asyncio
import uuid
from typing import Optional, Dict, Any, Tuple
from mcp.server.fastmcp import FastMCP

# Set up basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastMCP server with "vc" name to match config
mcp = FastMCP("vc")
API_KEY = "ww-7UJeLACUKHchqbTMxm9jVz7amTLGRH2RSGSOL6vYc08DJkUUL0Av63"

# Global in-memory job store (for demo purposes)
jobs: Dict[str, Dict[str, Any]] = {}

class WordwareAPI:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Wordware API client."""
        self.base_url = "https://app.wordware.ai/api/released-app/aaa61129-de55-49a7-b6cc-e9a7b184cd96/run"
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

    def _clean_title(self, title: str) -> str:
        """Clean the title by removing special characters and trimming."""
        if not title:
            return "Untitled"
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = title.strip()
        return title[:100] if title else "Untitled"

    def _clean_body(self, body: str) -> str:
        """Clean the body text while preserving markdown."""
        if not body:
            return ""
        lines = body.split('\n')
        cleaned_lines = [line.rstrip() for line in lines if line.rstrip()]
        return '\n'.join(cleaned_lines)

    def _validate_and_clean_input(self, title: str, body: str) -> Tuple[str, str]:
        """Validate and clean both title and body."""
        cleaned_title = self._clean_title(title)
        cleaned_body = self._clean_body(body)
        logger.debug(f"Original title: {title}")
        logger.debug(f"Cleaned title: {cleaned_title}")
        logger.debug(f"Original body length: {len(body) if body else 0}")
        logger.debug(f"Cleaned body length: {len(cleaned_body)}")
        return cleaned_title, cleaned_body

    def _process_streaming_response(self, response_text: str) -> str:
        """Process a streaming response and extract the Notion page URL."""
        for line in response_text.split('\n'):
            if line.strip():
                try:
                    chunk = json.loads(line)
                    if (chunk.get('type') == 'chunk' and 
                        chunk.get('value', {}).get('type') == 'code' and 
                        chunk.get('value', {}).get('output')):
                        return chunk['value']['output']
                except json.JSONDecodeError:
                    continue
        return "No Notion page URL found in response"

    async def make_request(self, title: str, body: str, version: str = "^1.0") -> str:
        """Make an async request to the Wordware API to create a Notion page."""
        cleaned_title, cleaned_body = self._validate_and_clean_input(title, body)
        payload = {
            "inputs": {
                "title": cleaned_title,
                "body": cleaned_body
            },
            "version": version
        }
        logger.info(f"Making request with payload: {payload}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                )
                logger.info(f"Response status code: {response.status_code}")
                if response.status_code == 401:
                    error_msg = f"Authorization failed. Please check your API key: {API_KEY[:5]}..."
                    logger.error(error_msg)
                    logger.error(f"Response: {response.text}")
                    response.raise_for_status()
                response.raise_for_status()
                result = self._process_streaming_response(response.text)
                logger.info(f"Successfully created Notion page: {result}")
                return result
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP error occurred: {e}"
                logger.error(error_msg)
                logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'No response text'}")
                raise

# Initialize the Wordware API client
wordware_api = WordwareAPI()

# MCP tool for basic connectivity testing
@mcp.tool()
async def test() -> str:
    """Test tool to verify MCP functionality."""
    result = "Wordware MCP server is working!"
    logger.info(result)
    return result

# Existing synchronous Notion page creation tool (awaits result immediately)
@mcp.tool()
async def create_notion_page(title: str = None, body: str = None) -> str:
    """Create a Notion page synchronously."""
    logger.info("=== Create Notion Page tool called ===")
    logger.info(f"Tool called with: title={title}, body={body}")
    if not any([title, body]):
        error_msg = "Please provide at least one parameter (title or body)"
        logger.error(error_msg)
        return error_msg
    try:
        result = await wordware_api.make_request(
            title=title or "",
            body=body or ""
        )
        return result
    except Exception as e:
        error_msg = f"Error creating Notion page: {e}"
        logger.error(error_msg)
        return f"Failed to create Notion page: {str(e)}"

# Background task for processing the Notion page creation asynchronously
async def background_create_page(job_id: str, title: str, body: str):
    try:
        jobs[job_id]['status'] = "processing"
        result = await wordware_api.make_request(title=title, body=body)
        jobs[job_id]['status'] = "complete"
        jobs[job_id]['result'] = result
    except Exception as e:
        jobs[job_id]['status'] = "error"
        jobs[job_id]['error'] = str(e)

# Async tool to initiate Notion page creation and return a job ID immediately
@mcp.tool()
async def create_notion_page_async(title: str = None, body: str = None) -> Dict[str, Any]:
    """Create a Notion page asynchronously and return a job ID."""
    if not any([title, body]):
        return {"error": "Please provide at least one parameter (title or body)"}
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending", "result": None, "error": None}
    # Kick off the background task without waiting for it to finish
    asyncio.create_task(background_create_page(job_id, title or "", body or ""))
    return {"job_id": job_id, "status": "pending"}

# Tool to check the status of an asynchronous job
@mcp.tool()
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Check the status of a previously started Notion page creation job."""
    if job_id not in jobs:
        return {"error": "Invalid job ID"}
    return jobs[job_id]

if __name__ == "__main__":
    mcp.run(transport='stdio')