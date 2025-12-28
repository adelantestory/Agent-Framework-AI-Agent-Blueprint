"""
Analytics abstraction layer for agent observability.

Supports multiple backends:
- InMemoryAnalytics: Fast, real-time, in-memory storage
- AppInsightsAnalytics: Azure Application Insights (for future migration)
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
import threading
import json
from typing import Dict, List, Any


class AnalyticsBackend(ABC):
    """Abstract base class for analytics backends"""

    @abstractmethod
    def track_event(self, event_type: str, properties: dict):
        """Track a discrete event"""
        pass

    @abstractmethod
    def track_metric(self, name: str, value: float, properties: dict = None):
        """Track a numeric metric"""
        pass

    @abstractmethod
    def get_analytics(self) -> dict:
        """Get analytics summary"""
        pass

    @abstractmethod
    def export_to_file(self, filename: str):
        """Export analytics data to file"""
        pass

    def track_conversation(self, user_prompt: str = None, agent_output: str = None,
                          tokens: dict = None, duration_ms: float = None):
        """Track a conversation turn (optional, not all backends need this)"""
        pass

    def get_recent_conversations(self, limit: int = 20) -> list:
        """Get recent conversations (optional)"""
        return []


class InMemoryAnalytics(AnalyticsBackend):
    """
    In-memory analytics backend with thread-safe operations.
    Fast, real-time, perfect for development and small deployments.
    """

    def __init__(self):
        self.data = {
            "session_start": datetime.now().isoformat(),
            "total_events": 0,
            "events_by_type": defaultdict(int),
            "tool_usage_count": defaultdict(int),
            "tool_durations": defaultdict(list),
            "llm_calls": 0,
            "total_tokens": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "errors": [],
            "recent_events": [],  # Last 100 events for debugging
            "recent_conversations": []  # Last 20 full conversations
        }
        self.lock = threading.Lock()
        self.current_conversation = {}  # Temporary storage for ongoing conversation

    def track_event(self, event_type: str, properties: dict):
        """Track an event with properties"""
        with self.lock:
            self.data["total_events"] += 1
            self.data["events_by_type"][event_type] += 1

            # Keep last 100 events for debugging
            self.data["recent_events"].append({
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "properties": properties
            })
            if len(self.data["recent_events"]) > 100:
                self.data["recent_events"].pop(0)

            # Special handling for specific event types
            if event_type == "tool_call_start":
                tool_name = properties.get("tool_name")
                if tool_name:
                    self.data["tool_usage_count"][tool_name] += 1

            elif event_type == "tool_call_end":
                tool_name = properties.get("tool_name")
                duration = properties.get("duration_ms")
                if tool_name and duration is not None:
                    self.data["tool_durations"][tool_name].append(duration)

            elif event_type == "error":
                self.data["errors"].append({
                    "timestamp": datetime.now().isoformat(),
                    "message": properties.get("message"),
                    "details": properties
                })

    def track_metric(self, name: str, value: float, properties: dict = None):
        """Track a numeric metric"""
        with self.lock:
            # Special metrics
            if name == "llm_call":
                self.data["llm_calls"] += 1
            elif name == "tokens_total":
                self.data["total_tokens"] += int(value)
            elif name == "tokens_prompt":
                self.data["total_prompt_tokens"] += int(value)
            elif name == "tokens_completion":
                self.data["total_completion_tokens"] += int(value)

    def get_analytics(self) -> dict:
        """Get analytics summary with computed metrics"""
        with self.lock:
            # Calculate averages for tool durations
            avg_tool_duration = {}
            for tool, durations in self.data["tool_durations"].items():
                if durations:
                    avg_tool_duration[tool] = {
                        "avg_ms": round(sum(durations) / len(durations), 2),
                        "min_ms": min(durations),
                        "max_ms": max(durations),
                        "count": len(durations)
                    }

            # Calculate token metrics
            tokens_per_llm_call = (
                round(self.data["total_tokens"] / self.data["llm_calls"], 2)
                if self.data["llm_calls"] > 0 else 0
            )

            return {
                "session_start": self.data["session_start"],
                "total_events": self.data["total_events"],
                "events_by_type": dict(self.data["events_by_type"]),
                "tool_usage_count": dict(self.data["tool_usage_count"]),
                "tool_performance": avg_tool_duration,
                "llm_metrics": {
                    "total_calls": self.data["llm_calls"],
                    "total_tokens": self.data["total_tokens"],
                    "total_prompt_tokens": self.data["total_prompt_tokens"],
                    "total_completion_tokens": self.data["total_completion_tokens"],
                    "avg_tokens_per_call": tokens_per_llm_call
                },
                "error_count": len(self.data["errors"]),
                "recent_errors": self.data["errors"][-10:],  # Last 10 errors
                "recent_events_count": len(self.data["recent_events"])
            }

    def track_conversation(self, user_prompt: str = None, agent_output: str = None,
                          tokens: dict = None, duration_ms: float = None):
        """
        Track a conversation turn.
        Call with user_prompt to start, then with agent_output to complete.
        """
        with self.lock:
            if user_prompt is not None:
                # Start new conversation turn
                self.current_conversation = {
                    "timestamp": datetime.now().isoformat(),
                    "user_prompt": user_prompt,
                    "agent_output": None,
                    "tokens": None,
                    "duration_ms": None
                }

            if agent_output is not None and self.current_conversation:
                # Complete conversation turn
                self.current_conversation["agent_output"] = agent_output
                self.current_conversation["tokens"] = tokens
                self.current_conversation["duration_ms"] = duration_ms

                # Add to recent conversations
                self.data["recent_conversations"].append(dict(self.current_conversation))

                # Keep only last 20
                if len(self.data["recent_conversations"]) > 20:
                    self.data["recent_conversations"].pop(0)

                # Clear current
                self.current_conversation = {}

    def get_recent_conversations(self, limit: int = 20) -> list:
        """Get recent conversations"""
        with self.lock:
            return self.data["recent_conversations"][-limit:]

    def export_to_file(self, filename: str):
        """Export full analytics data to JSON file"""
        with self.lock:
            export_data = {
                **self.data,
                "exported_at": datetime.now().isoformat(),
                "analytics_summary": self.get_analytics()
            }

            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            return filename


class AppInsightsAnalytics(AnalyticsBackend):
    """
    Azure Application Insights backend (for future use).
    Requires: pip install opencensus-ext-azure
    """

    def __init__(self, connection_string: str = None):
        """
        Initialize Application Insights backend

        Args:
            connection_string: Azure Application Insights connection string
        """
        self.connection_string = connection_string
        self.logger = None
        self.metrics_exporter = None

        # Lazy initialization - only import if actually used
        if connection_string:
            self._initialize_app_insights()

    def _initialize_app_insights(self):
        """Initialize Application Insights SDK"""
        try:
            from opencensus.ext.azure.log_exporter import AzureLogHandler
            from opencensus.ext.azure import metrics_exporter
            import logging

            # Setup logger
            self.logger = logging.getLogger("agent_analytics")
            self.logger.addHandler(AzureLogHandler(
                connection_string=self.connection_string
            ))
            self.logger.setLevel(logging.INFO)

            # Setup metrics exporter
            self.metrics_exporter = metrics_exporter.new_metrics_exporter(
                connection_string=self.connection_string
            )

            print("[ANALYTICS] Application Insights initialized")

        except ImportError:
            print("[ANALYTICS] WARNING: opencensus-ext-azure not installed")
            print("[ANALYTICS] Install with: pip install opencensus-ext-azure")
            self.logger = None
            self.metrics_exporter = None

    def track_event(self, event_type: str, properties: dict):
        """Track event to Application Insights"""
        if self.logger:
            self.logger.info(f"agent_event_{event_type}", extra={
                'custom_dimensions': {
                    'event_type': event_type,
                    **properties
                }
            })

    def track_metric(self, name: str, value: float, properties: dict = None):
        """Track metric to Application Insights"""
        if self.metrics_exporter:
            # Note: Implementation depends on metrics_exporter API
            # This is a placeholder for future implementation
            pass

        if self.logger:
            self.logger.info(f"metric_{name}", extra={
                'custom_dimensions': {
                    'metric_name': name,
                    'value': value,
                    **(properties or {})
                }
            })

    def get_analytics(self) -> dict:
        """Application Insights doesn't support real-time pull queries"""
        return {
            "message": "Analytics are being sent to Azure Application Insights",
            "view_at": "https://portal.azure.com",
            "note": "Use Kusto queries in Azure Portal to view analytics"
        }

    def export_to_file(self, filename: str):
        """Not applicable for Application Insights"""
        return None


class MultiBackend(AnalyticsBackend):
    """
    Composite backend that sends analytics to multiple backends simultaneously.
    Useful for migration period or when you want both local and cloud analytics.
    """

    def __init__(self, backends: List[AnalyticsBackend]):
        self.backends = backends

    def track_event(self, event_type: str, properties: dict):
        for backend in self.backends:
            try:
                backend.track_event(event_type, properties)
            except Exception as e:
                print(f"[ANALYTICS] Error in backend {backend.__class__.__name__}: {e}")

    def track_metric(self, name: str, value: float, properties: dict = None):
        for backend in self.backends:
            try:
                backend.track_metric(name, value, properties)
            except Exception as e:
                print(f"[ANALYTICS] Error in backend {backend.__class__.__name__}: {e}")

    def get_analytics(self) -> dict:
        """Returns analytics from the first backend (typically InMemory)"""
        if self.backends:
            return self.backends[0].get_analytics()
        return {}

    def export_to_file(self, filename: str):
        """Export from first backend that supports it"""
        for backend in self.backends:
            try:
                result = backend.export_to_file(filename)
                if result:
                    return result
            except:
                continue
        return None


# Global analytics backend instance (configured in agent.py)
analytics_backend: AnalyticsBackend = None


def initialize_analytics(backend: AnalyticsBackend):
    """Initialize the global analytics backend"""
    global analytics_backend
    analytics_backend = backend
    print(f"[ANALYTICS] Initialized with {backend.__class__.__name__}")


def get_analytics_backend() -> AnalyticsBackend:
    """Get the current analytics backend"""
    return analytics_backend
