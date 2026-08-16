from dataclasses import dataclass
from langchain.tools import tool
from datetime import datetime
from langgraph.prebuilt import ToolRuntime
from zoneinfo import ZoneInfo

@dataclass
class Context:
    timezone: ZoneInfo

@tool
def current_datetime(runtime: ToolRuntime[Context]) -> str:
    """Get the current date and time."""
    return datetime.now(runtime.context.timezone).isoformat()

@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

@tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b