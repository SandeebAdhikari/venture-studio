"""DevTools neighborhood alignment examples."""

from __future__ import annotations

from app.agents.classification.alignment_preamble import alignment_namespace_preamble


def alignment_devtools_prompt_block() -> str:
    return (
        f"{alignment_namespace_preamble()}"
        "DevTools neighborhood — engineering platform and developer workflow pain.\n\n"
        "problem_category mapping guidance:\n"
        "- CI/CD, YAML pipelines, build templates → workflow\n"
        "- Local dev slowness, deployment environments → performance or workflow\n"
        "- API spec / OpenAPI authoring friction → workflow or missing_feature\n"
        "- Platform API developer experience (HubSpot, etc.) → ux_ui or missing_feature\n"
        "- Agentic code trust, MCP server discovery → workflow or performance\n\n"
        "Founder signal examples (problem_category | business_function_code | jtbd_code | consequence_code):\n"
        '- "Tired of YAML CI/CD configurations." → workflow | ci_cd | deploy_software | operational_overhead\n'
        '- "Local Rails page loads take 10+ seconds." → performance | deployment | deploy_software | operational_risk\n'
        '- "OpenAPI spec in YAML is tedious." → workflow | api_platform | publish_consume_apis | operational_overhead\n'
        '- "0 trust in the quality of generated code." → performance | developer_experience | improve_developer_workflow | operational_risk\n'
        '- "MCP server discovery is time-consuming." → workflow | agent_tooling | configure_agent_tools | operational_overhead\n\n'
        "NEGATIVE examples:\n"
        '- WRONG: manage_subscriptions for MCP/agent tooling (not SaaS billing)\n'
        '- WRONG: checkout_optimization for developer UX complaints\n'
        '- WRONG: fraud_prevention for internal security policy frustration\n'
    )
