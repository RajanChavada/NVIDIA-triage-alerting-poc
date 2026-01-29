"""
Kafka MCP Server - Model Context Protocol server for Kafka integration.

Exposes tools for event-driven architecture:
- publish_message(): Publish diagnostic messages to Kafka topics
- get_recent_messages(): Get recent messages from a topic
- check_consumer_lag(): Check consumer group lag for scaling decisions

This enables the agent to participate in the event-driven workflow.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json
import random
import uuid

from langchain_core.tools import tool


# In-memory mock Kafka for MVP
_mock_topics: Dict[str, List[Dict]] = defaultdict(list)


# Pre-populate with some mock messages
def _init_mock_data():
    """Initialize mock Kafka topics with sample data."""
    if _mock_topics:
        return
    
    # GPU alerts topic
    _mock_topics["gpu-alerts"].extend([
        {
            "key": str(uuid.uuid4()),
            "value": {
                "alert_type": "gpu_temperature_high",
                "gpu_id": 0,
                "node": "gpu-node-1",
                "temperature": 87,
                "threshold": 85,
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
            },
            "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
            "partition": 0,
            "offset": 100,
        },
        {
            "key": str(uuid.uuid4()),
            "value": {
                "alert_type": "gpu_memory_low",
                "gpu_id": 1,
                "node": "gpu-node-2",
                "free_memory_mb": 512,
                "threshold_mb": 1000,
                "timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(),
            },
            "timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(),
            "partition": 0,
            "offset": 101,
        },
    ])
    
    # Triage outcomes topic
    _mock_topics["triage-outcomes"].extend([
        {
            "key": str(uuid.uuid4()),
            "value": {
                "triage_id": str(uuid.uuid4()),
                "alert_id": str(uuid.uuid4()),
                "status": "approved",
                "action_taken": "scaled_replicas",
                "confidence": 0.92,
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            },
            "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            "partition": 0,
            "offset": 50,
        },
    ])


_init_mock_data()


@tool
def publish_message(
    topic: str,
    message: Dict[str, Any],
    key: str = None
) -> Dict[str, Any]:
    """
    Publish a message to a Kafka topic.
    
    Use this to:
    - Publish triage outcomes after processing
    - Send diagnostic messages for downstream consumers
    - Trigger other event-driven workflows
    
    Args:
        topic: Kafka topic name (e.g., "triage-outcomes", "agent-diagnostics")
        message: Message payload as dictionary
        key: Optional message key for partitioning
        
    Returns:
        Publish confirmation with offset
    """
    key = key or str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Get next offset
    offset = len(_mock_topics[topic])
    
    record = {
        "key": key,
        "value": message,
        "timestamp": timestamp,
        "partition": 0,
        "offset": offset,
    }
    
    _mock_topics[topic].append(record)
    
    return {
        "status": "success",
        "topic": topic,
        "partition": 0,
        "offset": offset,
        "timestamp": timestamp,
        "key": key,
    }


@tool
def get_recent_messages(
    topic: str,
    count: int = 10,
    from_offset: int = None
) -> List[Dict[str, Any]]:
    """
    Get recent messages from a Kafka topic.
    
    Use this to:
    - Check recent GPU alerts
    - Review past triage outcomes
    - Correlate events across topics
    
    Args:
        topic: Kafka topic name
        count: Maximum number of messages to return
        from_offset: Start from specific offset (None = latest)
        
    Returns:
        List of messages with metadata
    """
    messages = _mock_topics.get(topic, [])
    
    if from_offset is not None:
        messages = [m for m in messages if m["offset"] >= from_offset]
    
    # Return most recent N messages
    return messages[-count:]


@tool
def check_consumer_lag(
    consumer_group: str,
    topic: str = None
) -> Dict[str, Any]:
    """
    Check consumer group lag for a topic.
    
    Use this for:
    - Detecting processing bottlenecks
    - Scaling decisions (HPA triggers on lag)
    - Health monitoring
    
    Args:
        consumer_group: Consumer group ID
        topic: Specific topic (None = all topics for group)
        
    Returns:
        Lag information per partition
    """
    # Mock consumer groups
    mock_groups = {
        "triage-agents": {
            "gpu-alerts": {"partition_0": 2, "partition_1": 0},
            "error-logs": {"partition_0": 5},
        },
        "metrics-aggregator": {
            "metrics-stream": {"partition_0": 150, "partition_1": 145, "partition_2": 160},
        },
        "notification-service": {
            "triage-outcomes": {"partition_0": 0},
        },
    }
    
    if consumer_group not in mock_groups:
        return {
            "error": f"Consumer group '{consumer_group}' not found",
            "available_groups": list(mock_groups.keys()),
        }
    
    group_lag = mock_groups[consumer_group]
    
    if topic:
        if topic in group_lag:
            return {
                "consumer_group": consumer_group,
                "topic": topic,
                "lag_by_partition": group_lag[topic],
                "total_lag": sum(group_lag[topic].values()),
                "is_healthy": sum(group_lag[topic].values()) < 100,
            }
        else:
            return {"error": f"Topic '{topic}' not consumed by group '{consumer_group}'"}
    
    # Return all topics for this group
    total_lag = sum(sum(partitions.values()) for partitions in group_lag.values())
    return {
        "consumer_group": consumer_group,
        "topics": group_lag,
        "total_lag": total_lag,
        "is_healthy": total_lag < 500,
    }


@tool
def list_topics() -> List[Dict[str, Any]]:
    """
    List available Kafka topics.
    
    Returns:
        List of topics with metadata
    """
    # Standard topics for the triage system
    return [
        {
            "name": "gpu-alerts",
            "partitions": 2,
            "replication_factor": 3,
            "description": "GPU-related alerts from DCGM exporter",
        },
        {
            "name": "service-alerts",
            "partitions": 4,
            "replication_factor": 3,
            "description": "Service-level alerts (latency, errors, etc.)",
        },
        {
            "name": "triage-outcomes",
            "partitions": 2,
            "replication_factor": 3,
            "description": "Results of triage agent processing",
        },
        {
            "name": "agent-diagnostics",
            "partitions": 1,
            "replication_factor": 2,
            "description": "Agent self-diagnostics and debug info",
        },
        {
            "name": "remediation-commands",
            "partitions": 2,
            "replication_factor": 3,
            "description": "Approved remediation commands for execution",
        },
    ]


@tool
def get_topic_health(topic: str) -> Dict[str, Any]:
    """
    Get health status of a Kafka topic.
    
    Args:
        topic: Topic name
        
    Returns:
        Health metrics including throughput and consumer lag
    """
    messages = _mock_topics.get(topic, [])
    
    # Calculate mock throughput
    recent = [m for m in messages if datetime.fromisoformat(m["timestamp"]) > datetime.now() - timedelta(hours=1)]
    
    return {
        "topic": topic,
        "total_messages": len(messages),
        "messages_last_hour": len(recent),
        "throughput_per_minute": round(len(recent) / 60, 2),
        "oldest_message": messages[0]["timestamp"] if messages else None,
        "newest_message": messages[-1]["timestamp"] if messages else None,
        "is_healthy": True,
    }


class KafkaMCPServer:
    """
    MCP Server wrapper for Kafka tools.
    
    Packages Kafka tools for MCP protocol compatibility.
    """
    
    def __init__(self, bootstrap_servers: str = "kafka:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.tools = [
            publish_message,
            get_recent_messages,
            check_consumer_lag,
            list_topics,
            get_topic_health,
        ]
    
    def list_tools(self) -> List[str]:
        """List available tools."""
        return [t.name for t in self.tools]
    
    def get_tool(self, name: str):
        """Get a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
