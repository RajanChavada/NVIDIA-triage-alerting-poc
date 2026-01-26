"""
Elasticsearch Tool - Mock log querying logic for SaturnV/Selene clusters.
"""
from typing import List, Dict, Any
import random
from datetime import datetime, timedelta

def query_elasticsearch_logs(service_name: str, query: str, size: int = 5) -> List[Dict[str, Any]]:
    """
    Mock querying logs from Elasticsearch.
    
    In a real scenario, this would query NVIDIA's internal log aggregation systems.
    """
    print(f"🔍 [TOOL] Querying Elasticsearch for logs: {service_name} (query: {query})...")
    
    # Simulate API latency
    import time
    time.sleep(2.0)
    
    log_templates = [
        "ERROR: Connection refused to database after 3 retries",
        "WARN: Low memory detected on pod auth-service-v2-abcde",
        "INFO: Processing request ID {id} - latency 250ms",
        "ERROR: Segmentation fault in NVSCI driver component",
        "CRITICAL: Resource deadlock detected in connection pool"
    ]
    
    logs = []
    now = datetime.utcnow()
    
    for i in range(size):
        logs.append({
            "timestamp": (now - timedelta(seconds=i*30)).isoformat(),
            "service": service_name,
            "level": "ERROR" if "error" in query.lower() else "INFO",
            "message": random.choice(log_templates).format(id=random.randint(1000, 9999)),
            "metadata": {
                "cluster": random.choice(["SaturnV", "Selene"]),
                "pod_id": f"{service_name}-v2-{random.randint(100, 999)}"
            }
        })
        
    return logs

# LangChain Tool Definition
from langchain_core.tools import tool

@tool
def search_logs(service_name: str, query: str, num_results: int = 5):
    """
    Search for logs in Elasticsearch/Kibana for a specific service.
    Use this to find specific error messages, stack traces, or systemic issues.
    """
    return query_elasticsearch_logs(service_name, query, size=num_results)
