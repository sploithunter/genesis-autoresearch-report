#!/usr/bin/env python3
"""
DDS Pattern Service - Verified DDS Code Pattern Library

A Genesis service that provides verified, working DDS code patterns.
General-purpose DDS development aid, not task-specific.
"""
import logging, asyncio, json, os
from typing import Dict, Any
from genesis_lib.decorators import genesis_function
from genesis_lib.monitored_service import MonitoredService

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    force=True)
logger = logging.getLogger("dds_pattern_service")

REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "reference_data")


def _load_json(filename):
    path = os.path.join(REFERENCE_DIR, filename)
    with open(path) as f:
        return json.load(f)


class DDSPatternService(MonitoredService):
    """Provides verified DDS code patterns and QoS recipes via Genesis functions."""

    def __init__(self, domain_id=55):
        self._patterns = _load_json("patterns.json")["patterns"]
        self._recipes = _load_json("qos_recipes.json")["recipes"]
        super().__init__("DDSPatternService", capabilities=["dds", "code_patterns"],
                         domain_id=domain_id)
        self._advertise_functions()

    @genesis_function()
    async def get_pattern(self, pattern_name: str, request_info=None) -> Dict[str, Any]:
        """Get a verified DDS code pattern by name.

        Args:
            pattern_name: Name of the pattern (example: rpc_requester)

        Returns:
            Dict with pattern description and verified code.
        """
        logger.info(f"get_pattern: {pattern_name}")
        self.publish_function_call_event("get_pattern", {"pattern_name": pattern_name}, request_info)

        pattern = self._patterns.get(pattern_name)
        if not pattern:
            available = list(self._patterns.keys())
            result = {"error": f"Pattern '{pattern_name}' not found. Available: {available}"}
        else:
            result = {
                "pattern_name": pattern_name,
                "category": pattern.get("category", ""),
                "description": pattern.get("description", ""),
                "code": pattern.get("code", ""),
            }

        self.publish_function_result_event("get_pattern", result, request_info)
        return result

    @genesis_function()
    async def list_patterns(self, category: str = "", request_info=None) -> Dict[str, Any]:
        """List available DDS code patterns, optionally filtered by category.

        Args:
            category: Filter by category (example: rpc)

        Returns:
            Dict with list of available pattern names and descriptions.
        """
        logger.info(f"list_patterns: category={category}")
        self.publish_function_call_event("list_patterns", {"category": category}, request_info)

        patterns = []
        for name, data in self._patterns.items():
            if not category or data.get("category") == category:
                patterns.append({
                    "name": name,
                    "category": data.get("category", ""),
                    "description": data.get("description", ""),
                })

        categories = sorted(set(d.get("category", "") for d in self._patterns.values()))
        result = {"patterns": patterns, "available_categories": categories}
        self.publish_function_result_event("list_patterns", result, request_info)
        return result

    @genesis_function()
    async def get_qos_recipe(self, goal: str, request_info=None) -> Dict[str, Any]:
        """Get QoS settings for a specific goal.

        Args:
            goal: What you want to achieve (example: late_joiner)

        Returns:
            Dict with required QoS settings, code, and critical notes.
        """
        logger.info(f"get_qos_recipe: {goal}")
        self.publish_function_call_event("get_qos_recipe", {"goal": goal}, request_info)

        recipe = self._recipes.get(goal)
        if not recipe:
            available = list(self._recipes.keys())
            result = {"error": f"Recipe '{goal}' not found. Available: {available}"}
        else:
            result = {"goal": goal, **recipe}

        self.publish_function_result_event("get_qos_recipe", result, request_info)
        return result


def main():
    logger.info("Starting DDS Pattern Service on domain 55...")
    service = None
    try:
        service = DDSPatternService(domain_id=55)
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        logger.info("DDS Pattern Service stopped.")


if __name__ == "__main__":
    main()
