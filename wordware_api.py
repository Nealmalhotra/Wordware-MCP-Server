import os
import json
import httpx
import asyncio
from typing import Optional, Dict, Any


class WordwareAPI:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Wordware API client.
        
        Args:
            api_key: The API key. If not provided, will try to get from environment variable.
        """
        self.api_key = api_key or os.getenv('WORDWARE_API_KEY')
        if not self.api_key:
            raise ValueError("API key is required. Either pass it directly or set WORDWARE_API_KEY environment variable.")
        
        self.base_url = "https://app.wordware.ai/api/released-app/aaa61129-de55-49a7-b6cc-e9a7b184cd96/run"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        print(f"Initialized API with key: {self.api_key[:5]}...")

    def _process_streaming_response(self, response_text: str) -> str:
        """Process a streaming response and extract the Notion page URL.
        
        Args:
            response_text: The raw response text
            
        Returns:
            The Notion page URL
        """
        for line in response_text.split('\n'):
            if line.strip():  # Skip empty lines
                try:
                    chunk = json.loads(line)
                    # Look for the code chunk that contains the Notion URL
                    if (chunk.get('type') == 'chunk' and 
                        chunk.get('value', {}).get('type') == 'code' and 
                        chunk.get('value', {}).get('output')):
                        return chunk['value']['output']
                except json.JSONDecodeError:
                    continue
        return "No Notion page URL found in response"

    async def make_request(self, title: str, body: str, version: str = "^1.0") -> str:
        """Make a request to the Wordware API.
        
        Args:
            title: The title for the request
            body: The body text for the request
            version: The API version to use (default: "^1.0")
            
        Returns:
            The Notion page URL
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        payload = {
            "inputs": {
                "title": title,
                "body": body
            },
            "version": version
        }
        print(f"Making request with payload: {payload}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                )
                
                print(f"Response status code: {response.status_code}")
                print(f"Response headers: {response.headers}")
                
                if response.status_code == 401:
                    print(f"Authorization failed. Please check your API key: {self.api_key[:5]}...")
                    print(f"Response: {response.text}")
                    response.raise_for_status()
                
                response.raise_for_status()
                return self._process_streaming_response(response.text)
            except httpx.HTTPStatusError as e:
                print(f"HTTP error occurred: {e}")
                print(f"Response: {e.response.text if hasattr(e, 'response') else 'No response text'}")
                raise

    def make_request_sync(self, title: str, body: str, version: str = "^1.0") -> str:
        """Synchronous version of make_request.
        
        Args:
            title: The title for the request
            body: The body text for the request
            version: The API version to use (default: "^1.0")
            
        Returns:
            The Notion page URL
        """
        payload = {
            "inputs": {
                "title": title,
                "body": body
            },
            "version": version
        }
        print(f"Making sync request with payload: {payload}")

        with httpx.Client() as client:
            try:
                response = client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                )
                
                print(f"Response status code: {response.status_code}")
                print(f"Response headers: {response.headers}")
                
                if response.status_code == 401:
                    print(f"Authorization failed. Please check your API key: {self.api_key[:5]}...")
                    print(f"Response: {response.text}")
                    response.raise_for_status()
                
                response.raise_for_status()
                return self._process_streaming_response(response.text)
            except httpx.HTTPStatusError as e:
                print(f"HTTP error occurred: {e}")
                print(f"Response: {e.response.text if hasattr(e, 'response') else 'No response text'}")
                raise

# Example usage
if __name__ == "__main__":
    # Example with API key
    try:
        api = WordwareAPI(api_key="ww-9tYgZDI6izh6AtcnkviYs5Mm2TzLNg7MtPMEfwjzHTya4AIDfBlIrV")
        
        # Example using synchronous method
        print("\n=== Testing Synchronous Request ===")
        result_sync = api.make_request_sync(
            title="Test Title",
            body="This is a test body"
        )
        print("Notion Page URL:", result_sync)
        
        # Example using asynchronous method
        print("\n=== Testing Asynchronous Request ===")
        async def async_example():
            result = await api.make_request(
                title="Test Title",
                body="This is a test body"
            )
            print("Notion Page URL:", result)
        
        # Run the async example
        asyncio.run(async_example())
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 