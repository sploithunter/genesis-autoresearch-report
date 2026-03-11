#!/usr/bin/env python3
"""
DDS Reference Service - RTI Connext API Reference Lookups

A Genesis service that provides RTI Connext DDS API reference information.
General-purpose DDS development aid, not task-specific.
"""
import logging, asyncio, json, os
from typing import Dict, Any
from genesis_lib.decorators import genesis_function
from genesis_lib.monitored_service import MonitoredService

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    force=True)
logger = logging.getLogger("dds_reference_service")

REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "reference_data")


def _load_json(filename):
    path = os.path.join(REFERENCE_DIR, filename)
    with open(path) as f:
        return json.load(f)


class DDSReferenceService(MonitoredService):
    """Provides RTI Connext DDS API reference lookups via Genesis functions."""

    def __init__(self, domain_id=55):
        self._api_data = {
            "rti.rpc": _load_json("rti_rpc_api.json"),
            "rti.types": _load_json("rti_types_api.json"),
            "rti.connextdds": _load_json("rti_connextdds_api.json"),
        }
        super().__init__("DDSReferenceService", capabilities=["dds", "api_reference"],
                         domain_id=domain_id)
        self._advertise_functions()

    @genesis_function()
    async def lookup_api(self, module: str, class_name: str = "", method_name: str = "",
                         request_info=None) -> Dict[str, Any]:
        """Look up an RTI Connext DDS Python API signature and usage.

        Args:
            module: RTI module name (example: rti.rpc)
            class_name: Class name to look up (example: Requester)
            method_name: Method name to look up (example: receive_replies)

        Returns:
            Dict with API signature, parameters, and usage example.
        """
        logger.info(f"lookup_api: module={module}, class={class_name}, method={method_name}")
        self.publish_function_call_event("lookup_api",
            {"module": module, "class_name": class_name, "method_name": method_name}, request_info)

        mod_data = self._api_data.get(module)
        if not mod_data:
            available = list(self._api_data.keys())
            result = {"error": f"Module '{module}' not found. Available: {available}"}
            self.publish_function_result_event("lookup_api", result, request_info)
            return result

        if not class_name:
            # Return module overview
            result = {"module": module, "overview": {k: v for k, v in mod_data.items()
                                                      if k not in ("module", "alias")}}
            self.publish_function_result_event("lookup_api", result, request_info)
            return result

        classes = mod_data.get("classes", {})
        cls_data = classes.get(class_name)
        if not cls_data:
            # Check decorators, functions, etc.
            for section in ("decorators", "functions", "enums", "builtin_topics",
                            "guid_formatting", "dynamic_types", "exceptions"):
                if section in mod_data:
                    entry = mod_data[section] if not isinstance(mod_data[section], dict) else mod_data[section].get(class_name)
                    if entry:
                        result = {"module": module, "name": class_name, "info": entry}
                        self.publish_function_result_event("lookup_api", result, request_info)
                        return result
            available = list(classes.keys())
            result = {"error": f"Class '{class_name}' not found in {module}. Available: {available}"}
            self.publish_function_result_event("lookup_api", result, request_info)
            return result

        if not method_name:
            result = {"module": module, "class": class_name, "info": cls_data}
            self.publish_function_result_event("lookup_api", result, request_info)
            return result

        methods = cls_data.get("methods", {})
        method_data = methods.get(method_name)
        if not method_data:
            props = cls_data.get("properties", {})
            prop_data = props.get(method_name)
            if prop_data:
                result = {"module": module, "class": class_name, "property": method_name,
                          "info": prop_data}
                self.publish_function_result_event("lookup_api", result, request_info)
                return result
            available = list(methods.keys()) + list(props.keys())
            result = {"error": f"Method '{method_name}' not found on {class_name}. Available: {available}"}
            self.publish_function_result_event("lookup_api", result, request_info)
            return result

        result = {"module": module, "class": class_name, "method": method_name,
                  "info": method_data}
        self.publish_function_result_event("lookup_api", result, request_info)
        return result

    @genesis_function()
    async def lookup_type_definition(self, approach: str = "idl_struct",
                                      request_info=None) -> Dict[str, Any]:
        """Look up how to define DDS types in Python.

        Args:
            approach: Type definition approach (example: idl_struct)

        Returns:
            Dict with type definition syntax, examples, and common mistakes.
        """
        logger.info(f"lookup_type_definition: approach={approach}")
        self.publish_function_call_event("lookup_type_definition",
            {"approach": approach}, request_info)

        types_data = self._api_data.get("rti.types", {})

        if approach in ("idl_struct", "@idl.struct", "struct"):
            decorators = types_data.get("decorators", {})
            result = decorators.get("@idl.struct", {"error": "No data for @idl.struct"})
        elif approach in ("dynamic", "DynamicData", "dynamic_data"):
            dds_data = self._api_data.get("rti.connextdds", {})
            result = dds_data.get("dynamic_types", {"error": "No dynamic type data"})
        elif approach == "idl.bound":
            funcs = types_data.get("functions", {})
            result = funcs.get("idl.bound", {"error": "No data for idl.bound"})
        else:
            result = {"error": f"Unknown approach '{approach}'. Try: idl_struct, dynamic, idl.bound"}

        self.publish_function_result_event("lookup_type_definition", result, request_info)
        return result

    @genesis_function()
    async def list_module_apis(self, module: str = "rti.connextdds",
                                request_info=None) -> Dict[str, Any]:
        """List available classes and methods in an RTI Connext module.

        Args:
            module: RTI module name (example: rti.connextdds)

        Returns:
            Dict with available classes, methods, and features.
        """
        logger.info(f"list_module_apis: module={module}")
        self.publish_function_call_event("list_module_apis", {"module": module}, request_info)

        mod_data = self._api_data.get(module)
        if not mod_data:
            result = {"error": f"Module '{module}' not found. Available: {list(self._api_data.keys())}"}
        else:
            summary = {}
            for key, val in mod_data.items():
                if key in ("module", "alias"):
                    summary[key] = val
                elif isinstance(val, dict):
                    summary[key] = list(val.keys())
                else:
                    summary[key] = str(val)[:200]
            result = {"module": module, "contents": summary}

        self.publish_function_result_event("list_module_apis", result, request_info)
        return result


def main():
    logger.info("Starting DDS Reference Service on domain 55...")
    service = None
    try:
        service = DDSReferenceService(domain_id=55)
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        logger.info("DDS Reference Service stopped.")


if __name__ == "__main__":
    main()
