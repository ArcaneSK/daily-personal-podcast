# Research brief: AI News
Date: 2026-04-29

## Top stories (prioritized)

### 1. Anthropic ships "Claude for Creative Work" with MCP connectors for Adobe, Blender, Autodesk, Ableton, and more
- **What happened:** On April 28, Anthropic launched a coordinated rollout of nine MCP-based connectors that let Claude drive professional creative software, with launch partners Adobe (50+ Creative Cloud apps), Blender, Autodesk Fusion, Ableton, Splice, Canva (Affinity), Resolume (Arena/Wire), and SketchUp. The connectors expose application APIs through the Model Context Protocol — so they're usable from any MCP-aware client, not just Claude — and Anthropic also joined the Blender Development Fund as a patron and seeded RISD, Ringling, and Goldsmiths with student/faculty access.
- **Why it matters:** This is the first time a frontier lab has coordinated a multi-vendor connector push into pro creative tooling, and it's a real-world stress test of MCP as the agent integration layer rather than just a developer protocol. Useful signal on whether MCP wins as the de facto standard.
- **Source:** https://www.anthropic.com/news/claude-for-creative-work
- **Date:** 2026-04-28

### 2. NVIDIA releases Nemotron 3 Nano Omni — open-weight 30B-A3B multimodal model targeting agent perception
- **What happened:** NVIDIA released Nemotron 3 Nano Omni on April 28 as open weights with open datasets and training recipes. It's a 30B hybrid MoE with 3B active parameters, 256K context, accepts text/image/audio/video/document/chart/UI input, and outputs text. NVIDIA claims it tops six leaderboards in document intelligence and audio-video understanding and delivers ~9x higher throughput than other open omni models at comparable latency. Available on Hugging Face, OpenRouter, build.nvidia.com, and 25+ partner platforms.
- **Why it matters:** A genuinely open multimodal model that's positioned specifically for the agent perception layer (computer use, document parsing, video reasoning) — relevant to the on-device / smaller-model parity thread, since 3B active params is in deployable territory. Worth watching whether independent benchmarks back the throughput claim.
- **Source:** https://blogs.nvidia.com/blog/nemotron-3-nano-omni-multimodal-ai-agents/
- **Date:** 2026-04-28
- **Continuity:** Feeds the recurring thread on whether smaller/open models are reaching parity with frontier APIs.

## Honorable mentions
- DeepSeek V4-Pro (1.6T total / 49B active, MIT-licensed, 1M context) released April 24 — Codeforces 3,206 (above GPT-5.4) and 80.6% on SWE-bench Verified, 0.2pt behind Claude Opus 4.6: https://api-docs.deepseek.com/news/news260424
- Anthropic MCP "design vulnerability" disclosure still rippling — OX Security's April analysis of STDIO command-execution behavior across 150M downloads / ~200k instances; Anthropic publicly called it "expected behavior," and CVE-2026-30623 was filed against the MCP SDK: https://thehackernews.com/2026/04/anthropic-mcp-design-vulnerability.html
- Claude Agent SDK churned through four minor versions in 13 days (v0.25 → v0.29.2), including a switch from explicit `"opus"` to `"default"` model aliasing and a dynamic-models payload — relevant to anyone embedding the SDK: https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk

## Open threads to revisit
- Independent benchmarks for Nemotron 3 Nano Omni's 9x-throughput and leaderboard claims — vendor self-reports only as of release day: https://blogs.nvidia.com/blog/nemotron-3-nano-omni-multimodal-ai-agents/
- DeepSeek V4 real-world coding evaluations — early independent reviews are mixed on whether it actually closes the gap with Opus 4.7 / GPT-5.5 outside the published benchmarks: https://www.geeky-gadgets.com/open-source-deepseek-v4-limitations/
- How the MCP "expected behavior" stance plays out — whether downstream SDK maintainers (LiteLLM, Cursor, LibreChat) push for a protocol-level fix or just patch around it: https://www.ox.security/blog/mcp-supply-chain-advisory-rce-vulnerabilities-across-the-ai-ecosystem/