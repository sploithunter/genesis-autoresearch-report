#!/usr/bin/env python3
"""
Genesis DDS Tool - CLI client for querying Genesis DDS services.

This is a lightweight Genesis client that connects to DDS tool services
on domain 55 and forwards queries. Used by coding agents during benchmarks.

Usage:
    python genesis_dds_tool.py --function lookup_api --args '{"module":"rti.rpc","class_name":"Requester"}'
    python genesis_dds_tool.py --function get_pattern --args '{"pattern_name":"rpc_requester"}'
    python genesis_dds_tool.py --function get_qos_recipe --args '{"goal":"late_joiner"}'
    python genesis_dds_tool.py --function diagnose_error --args '{"error_message":"AttributeError: ..."}'
    python genesis_dds_tool.py --list  # List all available functions
"""
import argparse
import asyncio
import json
import sys
import time
import os

# Add genesis_lib to path
GENESIS_DIR = os.environ.get("GENESIS_LIB_PATH",
    os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, GENESIS_DIR)

from genesis_lib.function_requester import FunctionRequester


async def list_functions(requester):
    """List all available functions from Genesis services."""
    funcs = requester.list_available_functions()
    result = []
    for f in funcs:
        result.append({
            "function_id": f["function_id"],
            "name": f["name"],
            "description": f["description"][:200],
            "service": f.get("service_name", ""),
        })
    return {"available_functions": result, "count": len(result)}


async def call_function(requester, function_name, args):
    """Call a function by name (searches available functions for a match)."""
    funcs = requester.list_available_functions()

    # Find function by name
    target = None
    for f in funcs:
        if f["name"] == function_name:
            target = f
            break

    if not target:
        # Fuzzy match
        for f in funcs:
            if function_name.lower() in f["name"].lower():
                target = f
                break

    if not target:
        available = [f["name"] for f in funcs]
        return {"error": f"Function '{function_name}' not found. Available: {available}"}

    result = await requester.call_function(target["function_id"], **args)
    return result


async def main():
    parser = argparse.ArgumentParser(description="Genesis DDS Tool - Query DDS development services")
    parser.add_argument("--function", "-f", help="Function name to call")
    parser.add_argument("--args", "-a", default="{}", help="JSON arguments for the function")
    parser.add_argument("--list", "-l", action="store_true", help="List available functions")
    parser.add_argument("--domain", "-d", type=int, default=55, help="DDS domain ID (default: 55)")
    parser.add_argument("--timeout", "-t", type=int, default=10, help="Timeout in seconds (default: 10)")
    args = parser.parse_args()

    requester = FunctionRequester(domain_id=args.domain)

    # Wait for function discovery (wait for all 3 services = ~8 functions)
    start = time.time()
    last_count = 0
    stable_since = 0
    while time.time() - start < args.timeout:
        funcs = requester.list_available_functions()
        count = len(funcs)
        if count > 0 and count == last_count:
            # Count hasn't changed — wait a bit more to ensure stability
            if stable_since == 0:
                stable_since = time.time()
            elif time.time() - stable_since > 2.0:
                break  # Stable for 2 seconds, good enough
        else:
            stable_since = 0
        last_count = count
        time.sleep(0.5)

    try:
        if args.list:
            result = await list_functions(requester)
        elif args.function:
            func_args = json.loads(args.args)
            result = await call_function(requester, args.function, func_args)
        else:
            parser.print_help()
            return

        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
    finally:
        requester.close()


if __name__ == "__main__":
    asyncio.run(main())
