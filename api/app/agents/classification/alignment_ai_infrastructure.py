"""AI Infrastructure neighborhood alignment examples."""

from __future__ import annotations

from app.agents.classification.alignment_preamble import alignment_namespace_preamble


def alignment_ai_infrastructure_prompt_block() -> str:
    return (
        f"{alignment_namespace_preamble()}"
        "AI Infrastructure neighborhood — LLM ops, agent tooling, GPU/compute, inference cost.\n\n"
        "problem_category mapping guidance:\n"
        "- MCP/agent tooling overhead → workflow or performance\n"
        "- LLM guardrails, eval pipelines, model quality → performance or missing_feature\n"
        "- Inference/API spend, Claude bill vs cloud spend → pricing\n"
        "- GPU rental unreliability, Colab quota denials → performance\n"
        "- Coding agent API spec access → missing_feature\n\n"
        "Founder signal examples (problem_category | business_function_code | jtbd_code | consequence_code):\n"
        '- "80% of engineering effort building guardrails." → performance | model_operations | operate_llm_systems | innovation_blocked\n'
        '- "Build a proper evaluation pipeline; tools have limitations." → missing_feature | llm_evaluation | evaluate_model_quality | operational_overhead\n'
        '- "Claude bill 3x our cloud spend; cutting AI tool spend." → pricing | inference_governance | govern_inference_spend | margin_erosion\n'
        '- "GPU rental performance nothing like console listing." → performance | gpu_compute | provision_compute | operational_risk\n'
        '- "Colab paid options don\'t work; wasting time on infrastructure." → performance | capacity_management | manage_capacity_quotas | operational_overhead\n'
        '- "MCP discovery time-consuming and not agentic." → workflow | agent_tooling | configure_agent_tools | operational_overhead\n'
        '- "MCP blows up the context window." → performance | agent_tooling | configure_agent_tools | operational_risk\n'
        '- "Coding agents struggle to get OpenAI API spec." → missing_feature | api_platform | publish_consume_apis | operational_risk\n\n'
        "NEGATIVE examples — common mislabels to avoid:\n"
        '- WRONG: payment_processor | accept_payments for GPU rental (Vast.ai, Colab)\n'
        '- WRONG: subscription_management | manage_subscriptions for MCP plans or token limits\n'
        '- WRONG: observability | monitor_systems as catch-all for AI infra pain\n'
        '- WRONG: fraud_prevention | prevent_fraud for any AI/ML complaint\n'
    )
