"""Allow running as: python -m src.mcp_server"""
from src.mcp_server.server import main
import asyncio

asyncio.run(main())
