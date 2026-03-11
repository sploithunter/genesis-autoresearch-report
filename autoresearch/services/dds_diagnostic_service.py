#!/usr/bin/env python3
"""
DDS Diagnostic Service - Error Diagnosis and QoS Compatibility

A Genesis service that diagnoses DDS errors and checks QoS compatibility.
General-purpose DDS development aid, not task-specific.
"""
import logging, asyncio, json, os
from typing import Dict, Any
from genesis_lib.decorators import genesis_function
from genesis_lib.monitored_service import MonitoredService

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    force=True)
logger = logging.getLogger("dds_diagnostic_service")

REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "reference_data")


def _load_json(filename):
    path = os.path.join(REFERENCE_DIR, filename)
    with open(path) as f:
        return json.load(f)


class DDSDiagnosticService(MonitoredService):
    """Diagnoses DDS errors and checks QoS compatibility via Genesis functions."""

    def __init__(self, domain_id=55):
        self._errors = _load_json("common_errors.json")["errors"]
        self._recipes = _load_json("qos_recipes.json")["recipes"]
        super().__init__("DDSDiagnosticService", capabilities=["dds", "diagnostics"],
                         domain_id=domain_id)
        self._advertise_functions()

    @genesis_function()
    async def diagnose_error(self, error_message: str, context: str = "",
                              request_info=None) -> Dict[str, Any]:
        """Diagnose a DDS error message and suggest fixes.

        Args:
            error_message: The error message or symptom (example: AttributeError: module 'rti.rpc' has no attribute 'Client')
            context: Additional context about what you were trying to do (example: creating an RPC client)

        Returns:
            Dict with likely cause and suggested fix.
        """
        logger.info(f"diagnose_error: {error_message[:100]}")
        self.publish_function_call_event("diagnose_error",
            {"error_message": error_message, "context": context}, request_info)

        # Exact match first
        if error_message in self._errors:
            diagnosis = self._errors[error_message]
            result = {"error_message": error_message, "matched": True,
                      "cause": diagnosis["cause"], "fix": diagnosis["fix"]}
            self.publish_function_result_event("diagnose_error", result, request_info)
            return result

        # Substring match
        matches = []
        error_lower = error_message.lower()
        for known_error, diagnosis in self._errors.items():
            # Check if key phrases from the known error appear in the input
            key_phrases = [p.strip().lower() for p in known_error.split("'") if len(p.strip()) > 3]
            if any(phrase in error_lower for phrase in key_phrases):
                matches.append({"known_error": known_error, **diagnosis})

        if matches:
            result = {"error_message": error_message, "matched": True,
                      "possible_diagnoses": matches}
        else:
            result = {"error_message": error_message, "matched": False,
                      "suggestion": "No exact match found. Try looking up the API with lookup_api or get_pattern functions.",
                      "common_issues": list(self._errors.keys())[:5]}

        self.publish_function_result_event("diagnose_error", result, request_info)
        return result

    @genesis_function()
    async def check_qos_compatibility(self, writer_qos: str, reader_qos: str,
                                       request_info=None) -> Dict[str, Any]:
        """Check if writer and reader QoS settings are compatible.

        Args:
            writer_qos: Writer QoS description (example: TRANSIENT_LOCAL, RELIABLE, KEEP_ALL)
            reader_qos: Reader QoS description (example: VOLATILE, BEST_EFFORT, KEEP_LAST)

        Returns:
            Dict with compatibility analysis and recommendations.
        """
        logger.info(f"check_qos_compatibility: writer={writer_qos}, reader={reader_qos}")
        self.publish_function_call_event("check_qos_compatibility",
            {"writer_qos": writer_qos, "reader_qos": reader_qos}, request_info)

        issues = []
        recommendations = []

        w = writer_qos.upper()
        r = reader_qos.upper()

        # Durability check
        if "TRANSIENT_LOCAL" in w and "VOLATILE" in r:
            issues.append("Durability mismatch: writer is TRANSIENT_LOCAL but reader is VOLATILE. Reader may not request cached samples.")
            recommendations.append("Set reader durability to TRANSIENT_LOCAL to match writer.")
        if "VOLATILE" in w and "TRANSIENT_LOCAL" in r:
            issues.append("Writer is VOLATILE - no samples are cached for late joiners regardless of reader settings.")
            recommendations.append("Set writer durability to TRANSIENT_LOCAL if late-joiner support is needed.")

        # Reliability check
        if "RELIABLE" in w and "BEST_EFFORT" in r:
            issues.append("Reader (BEST_EFFORT) requesting from RELIABLE writer is allowed but won't get resend benefits.")
        if "BEST_EFFORT" in w and "RELIABLE" in r:
            issues.append("INCOMPATIBLE: Reader requires RELIABLE but writer offers only BEST_EFFORT. They will NOT match!")
            recommendations.append("Set writer to RELIABLE to match reader requirement.")
        if "TRANSIENT_LOCAL" in w and "BEST_EFFORT" in w:
            issues.append("TRANSIENT_LOCAL with BEST_EFFORT: cached data may not be reliably delivered to late joiners. RELIABLE is needed to activate resend mechanism.")
            recommendations.append("Set writer to RELIABLE for proper late-joiner delivery.")

        # History check
        if "KEEP_LAST" in w and "KEEP_ALL" not in w:
            issues.append("Writer uses KEEP_LAST (check depth). Default depth=1 only keeps the most recent sample.")
            recommendations.append("If multiple samples must reach late joiners, use KEEP_ALL or increase KEEP_LAST depth.")

        compatible = len([i for i in issues if "INCOMPATIBLE" in i]) == 0
        result = {
            "compatible": compatible,
            "issues": issues if issues else ["No issues detected."],
            "recommendations": recommendations if recommendations else ["QoS settings look compatible."],
            "writer_qos": writer_qos,
            "reader_qos": reader_qos,
        }

        self.publish_function_result_event("check_qos_compatibility", result, request_info)
        return result


def main():
    logger.info("Starting DDS Diagnostic Service on domain 55...")
    service = None
    try:
        service = DDSDiagnosticService(domain_id=55)
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        logger.info("DDS Diagnostic Service stopped.")


if __name__ == "__main__":
    main()
