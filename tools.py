TOOL_CONFIG = {
    "notion_page": {
        "description": "Creates a Notion page using the Wordware API",
        "payload_template": {
            "inputs": {
                "title": "{title}",
                "body": "{body}"
            },
            "version": "^1.0"
        },
        "api_url": "https://app.wordware.ai/api/released-app/aaa61129-de55-49a7-b6cc-e9a7b184cd96/run",
        "async": True
    },
    "google_search": {
        "description": "Searches Google using a Wordware-powered tool",
        "payload_template": {
            "inputs": {
                "query": "{query}"
            },
            "version": "^1.0"
        },
        "api_url": "https://app.wordware.ai/api/released-app/6e7817c6-5f67-4905-ab5b-18f28c333637/run",
        "async": True
    },
    "wikipedia_lookup": {
        "description": "Fetches information from Wikipedia based on a term",
        "payload_template": {
            "inputs": {
                "term": "{term}"
            },
            "version": "^1.0"
        },
        "api_url": "https://app.wordware.ai/api/released-app/4d4b0a16-d62b-4ec2-a43d-ac8c1ee18de8/run",
        "async": True
    },
    "google_news": {
        "description": "Gets the latest news using Google News",
        "payload_template": {
            "inputs": {
                "news": "{news}"
            },
            "version": "^1.0"
        },
        "api_url": "https://app.wordware.ai/api/released-app/8e468bc7-f612-4e0b-a2c5-4451c03e16c1/run",
        "async": True
    }
}