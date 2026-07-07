import time
import re
import logging
from agent_graph.config import settings

logger = logging.getLogger("agent_graph.llm_helper")

def safe_llm_invoke(structured_llm, messages, max_retries=10):
    """Paces LLM API calls with a consistent 4.0-second delay to respect the 20 RPM ceiling,
    and applies adaptive retry/backoff on 429/ResourceExhausted errors and transient network drops.
    """
    # 1. Proactive pacing: sleep 4.0 seconds (skipped in mock mode)
    if not settings.MOCK_LLM:
        logger.info("Pacing LLM call: sleeping 4.0 seconds...")
        time.sleep(4.0)
        
    for attempt in range(1, max_retries + 1):
        try:
            return structured_llm.invoke(messages)
        except Exception as e:
            err_str = str(e)
            is_rate_limit = any(term in err_str.lower() for term in ["429", "resource_exhausted", "rate", "quota", "limit"])
            is_network_fault = any(term in err_str.lower() for term in ["gaierror", "getaddrinfo", "connection", "timeout", "dns", "http"])
            
            # If it's a daily limit error, raise immediately because it won't reset in a few minutes
            if is_rate_limit and "requestsperday" in err_str.lower():
                logger.error("Daily Gemini API request quota exceeded (RequestsPerDay). Failing run immediately.")
                raise e
                
            if (is_rate_limit or is_network_fault) and attempt < max_retries:
                # Calculate sleep duration
                if is_rate_limit:
                    sleep_dur = 35.0  # Safe default to reset 1-minute window
                    sec_match = re.search(r"retry in (\d+(\.\d+)?)s", err_str, re.IGNORECASE)
                    if sec_match:
                        sleep_dur = float(sec_match.group(1)) + 2.0
                    else:
                        ms_match = re.search(r"retry in (\d+(\.\d+)?)ms", err_str, re.IGNORECASE)
                        if ms_match:
                            sleep_dur = (float(ms_match.group(1)) / 1000.0) + 1.0
                else:
                    # For network drops, sleep 5 seconds and retry
                    sleep_dur = 5.0
                    
                logger.warning(
                    f"Fault hit (attempt {attempt}/{max_retries}). "
                    f"Retrying in {sleep_dur:.1f}s. Error detail: {err_str}"
                )
                time.sleep(sleep_dur)
            else:
                logger.error(f"LLM invoke failed: {err_str}")
                raise e
