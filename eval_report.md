# Benchmark Evaluation Report

This report summarizes the performance of the **Multi-Agent Coding Assistant** on the 5 approved benchmark tasks running against the real Gemini API (`MOCK_LLM=false`).

---

## Executive Summary

| Metric | Value |
|---|---|
| **Evaluation Date** | 2026-07-07 20:13:08 |
| **Total Benchmark Tasks** | 5 |
| **Successful Tasks** | 0 / 5 |
| **Success Rate** | 0.0% |
| **Total Execution Time** | 3.38 minutes |
| **Average Task Time** | 40.61 seconds |
| **Average Routing Cycles** | 2.4 iterations |

---

## Detailed Task Performance

| Task ID | Task Name | Status | Iterations | Time (s) | File Count |
|---|---|---|---|---|---|
| `task_1_lru_cache` | LRU Cache | ❌ FAILED | 4 | 40.31 | 0 |
| `task_2_rate_limiter` | Token Bucket Rate Limiter | ❌ FAILED | 2 | 40.02 | 0 |
| `task_3_csv_validator` | Multi-File CSV Validator | ❌ FAILED | 2 | 41.31 | 0 |
| `task_4_run_length_encoder` | Run-Length Encoder | ❌ FAILED | 2 | 40.50 | 0 |
| `task_5_markdown_to_html` | Markdown to HTML Converter | ❌ FAILED | 2 | 40.91 | 0 |

---

## Task Details Breakdown

### LRU Cache
*   **Status**: Failed (failed)
*   **Orchestrator Iterations**: 4
*   **Time Elapsed**: 40.31 seconds
*   **Generated Files** (0):
    *   No files created.

*   **Error Encountered**:
    > [SUPERVISOR NODE FAILURE] Action: Routed to failed | Reasoning: Failed to call Gemini API for supervisor decision: Error calling model 'gemini-2.5-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\nPlease retry in 33.517326587s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'model': 'gemini-2.5-flash', 'location': 'global'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '33s'}]}}

### Token Bucket Rate Limiter
*   **Status**: Failed (failed)
*   **Orchestrator Iterations**: 2
*   **Time Elapsed**: 40.02 seconds
*   **Generated Files** (0):
    *   No files created.

*   **Error Encountered**:
    > [SUPERVISOR NODE FAILURE] Action: Routed to failed | Reasoning: Failed to call Gemini API for supervisor decision: Error calling model 'gemini-2.5-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\nPlease retry in 53.585615149s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '53s'}]}}

### Multi-File CSV Validator
*   **Status**: Failed (failed)
*   **Orchestrator Iterations**: 2
*   **Time Elapsed**: 41.31 seconds
*   **Generated Files** (0):
    *   No files created.

*   **Error Encountered**:
    > [SUPERVISOR NODE FAILURE] Action: Routed to failed | Reasoning: Failed to call Gemini API for supervisor decision: Error calling model 'gemini-2.5-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\nPlease retry in 12.284057564s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '12s'}]}}

### Run-Length Encoder
*   **Status**: Failed (failed)
*   **Orchestrator Iterations**: 2
*   **Time Elapsed**: 40.50 seconds
*   **Generated Files** (0):
    *   No files created.

*   **Error Encountered**:
    > [SUPERVISOR NODE FAILURE] Action: Routed to failed | Reasoning: Failed to call Gemini API for supervisor decision: Error calling model 'gemini-2.5-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\nPlease retry in 31.736512287s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '31s'}]}}

### Markdown to HTML Converter
*   **Status**: Failed (failed)
*   **Orchestrator Iterations**: 2
*   **Time Elapsed**: 40.91 seconds
*   **Generated Files** (0):
    *   No files created.

*   **Error Encountered**:
    > [SUPERVISOR NODE FAILURE] Action: Routed to failed | Reasoning: Failed to call Gemini API for supervisor decision: Error calling model 'gemini-2.5-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash\nPlease retry in 50.94309318s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-flash'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '50s'}]}}
