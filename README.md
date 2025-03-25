Hey guys!

Here is the code for MCP server. 

I have split it up into 2 distinct features but they are pretty easy to combine — just easier to show as seperate.
- To run, clone repo and add a .env file with wordware API key.
- Install uv and set up our Python project and environment

Now it diverges for which features you want to test. In Claude, if you navigate to the developer page, there will be a button to edit the mcp config file. For testing async tasks,
put wordware_api.py or if you want to test ReAct agent and dynamically adding tools put ReActTool.py

Then when you restart claude you will be able to use the Wordware tools!
