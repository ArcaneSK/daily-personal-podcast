## SEGMENT_BREAK 02-ai-news

[NARRATOR] It's Wednesday, April 29th. Here's what actually moved in AI in the last 24 hours.

[HOST_A] Okay Jordan, lead story — Anthropic shipped something called "Claude for Creative Work." What is it?

[HOST_B] It's a coordinated MCP connector rollout, and the partner list is the interesting part. Adobe across 50-plus Creative Cloud apps, Blender, Autodesk Fusion, Ableton, Splice, Canva's Affinity, Resolume, and SketchUp. All landed yesterday, April 28th, per Anthropic's own announcement.

[HOST_A] So Claude can now drive Photoshop and Blender directly?

[HOST_B] Through their APIs, yes — but the part I care about is that these are MCP connectors. Any MCP-aware client can use them. It's not a Claude lock-in play. Anthropic also joined the Blender Development Fund as a patron and seeded RISD, Ringling, and Goldsmiths with access.

[HOST_A] Why does that matter beyond "cool, AI in Photoshop"?

[HOST_B] Because it's the first time a frontier lab has coordinated a multi-vendor push into pro creative tooling. It's a real stress test of whether MCP becomes the de facto agent integration layer or stays a dev-tools protocol. That's the actual signal.

[HOST_A] Speaking of MCP — wasn't there an OX Security disclosure still hanging over it?

[HOST_B] Yeah, The Hacker News reported the design-vulnerability ripple is ongoing — STDIO command execution across roughly 200,000 instances, CVE-2026-30623 filed against the MCP SDK, and Anthropic is publicly calling it "expected behavior." So this big creative push is happening while the protocol's security model is contested. Worth flagging.

[HOST_A] Noted. Story two — NVIDIA dropped an open model?

[HOST_B] Nemotron 3 Nano Omni, also April 28th. Open weights, open datasets, open training recipes. It's a 30 billion parameter hybrid MoE with 3 billion active, 256K context, and it ingests text, image, audio, video, documents, charts, and UI screenshots.

[HOST_A] Three billion active parameters — that's deployable territory.

[HOST_B] That's the thread. NVIDIA is positioning this squarely at the agent perception layer — computer use, document parsing, video reasoning. They claim it tops six leaderboards in document intelligence and audio-video understanding, and roughly 9x throughput versus other open omni models at comparable latency.

[HOST_A] What's actually new there?

[HOST_B] The 9x number, if it holds. But it's a vendor self-report on release day. Independent benchmarks haven't landed yet, so I'd hold the applause until someone outside NVIDIA confirms it.

[HOST_A] Anything else on the open-model front?

[HOST_B] Quick mention — DeepSeek V4-Pro from last week, 1.6 trillion total, 49 billion active, MIT-licensed, 1 million context. Per DeepSeek's API docs they're claiming Codeforces 3,206 and 80.6 percent on SWE-bench Verified, putting it 0.2 points behind Claude Opus 4.6. Geeky Gadgets is already reporting independent reviews are mixed on whether it actually closes the gap outside the published benchmarks.

[HOST_A] And one for the SDK watchers?

[HOST_B] The Claude Agent SDK shipped four minor versions in 13 days on npm — v0.25 through v0.29.2. Notable change: the explicit "opus" model string is now aliased to "default," and there's a dynamic-models payload. If you're embedding it, go read the changelog before you upgrade.

[HOST_A] Punchy day. Connectors, an open omni model, and an SDK that won't sit still.

[HOST_B] That's the read.