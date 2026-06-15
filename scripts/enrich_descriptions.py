"""
enrich_descriptions.py
Rewrites the 'desc' field in data/repos.json using:
  1. Curated descriptions for ~200 well-known repos
  2. Rule-based enrichment for the rest: clean existing desc + "— for [audience]"
  3. Name-derived fallback for empty descriptions

Output: data/repos_enriched.json  (same structure as repos.json)
"""

import json, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC  = ROOT / "data" / "repos.json"
OUT  = ROOT / "data" / "repos_enriched.json"

# ── curated descriptions for well-known repos ─────────────────────────────────
KNOWN = {
    # ── Web & Frameworks ──────────────────────────────────────────────────────
    "vercel/next.js":
        "Full-stack React framework with SSR, SSG, and App Router — for developers building production web applications",
    "facebook/react":
        "Declarative, component-based UI library for building web and native interfaces — for JavaScript and TypeScript developers",
    "vuejs/vue":
        "Progressive JavaScript framework for building reactive UIs with a gentle learning curve — for frontend developers",
    "sveltejs/svelte":
        "Compiler-based UI framework that ships zero runtime overhead — for developers who want fast, lightweight web apps",
    "twbs/bootstrap":
        "Most popular CSS framework for responsive, mobile-first web design with pre-built components — for frontend developers and designers",
    "tailwindlabs/tailwindcss":
        "Utility-first CSS framework for building custom designs directly in markup — for frontend developers who prefer atomic styling",
    "nuxt/nuxt":
        "Vue meta-framework with SSR, SSG, file-based routing, and auto-imports — for Vue developers building full-stack applications",
    "remix-run/remix":
        "Full-stack web framework built on web standards with nested routing and progressive enhancement — for React developers building web apps",
    "vitejs/vite":
        "Lightning-fast frontend build tool and dev server powered by native ES modules — for modern web developers",
    "nodejs/node":
        "Asynchronous JavaScript runtime built on V8 for scalable server-side applications — for backend and full-stack JavaScript developers",
    "expressjs/express":
        "Minimal and flexible Node.js web application framework — for backend developers building REST APIs and web servers in JavaScript",
    "django/django":
        "Batteries-included Python web framework following the MTV pattern — for developers building complex, database-backed web applications",
    "pallets/flask":
        "Lightweight WSGI Python micro-framework for building APIs and web apps — for Python developers who prefer simplicity and explicit design",
    "tiangolo/fastapi":
        "Modern Python web framework with automatic OpenAPI docs, async support, and Pydantic validation — for Python API developers",
    "nestjs/nest":
        "Progressive Node.js framework for building server-side apps using TypeScript and decorators — for enterprise backend developers",
    "strapi/strapi":
        "Open-source headless CMS with a customizable API and admin panel — for teams building content-driven applications",
    "directus/directus":
        "Open data platform that wraps any SQL database with a REST/GraphQL API and admin UI — for developers who need an instant backend",
    "WordPress/gutenberg":
        "React-based block editor powering the WordPress editing experience — for WordPress developers and contributors",

    # ── AI / LLMs / Generative ───────────────────────────────────────────────
    "AUTOMATIC1111/stable-diffusion-webui":
        "Feature-rich browser UI for Stable Diffusion with inpainting, img2img, upscaling, and 500+ extensions — for AI artists and image generation enthusiasts",
    "comfyanonymous/ComfyUI":
        "Node-graph visual workflow builder for Stable Diffusion and diffusion pipelines — for power users who want full control over AI image generation",
    "invoke-ai/InvokeAI":
        "Professional creative toolkit for Stable Diffusion with unified canvas, workflows, and model management — for artists and studios using AI image generation",
    "openai/whisper":
        "Multilingual speech recognition model that transcribes and translates audio in 99 languages — for developers adding transcription or voice features",
    "SYSTRAN/faster-whisper":
        "Up to 4× faster Whisper reimplementation via CTranslate2 with lower memory usage — for developers needing efficient, production-grade transcription",
    "collabora/WhisperLive":
        "Near-real-time Whisper transcription server with WebSocket streaming — for developers building live captioning and voice interfaces",
    "huggingface/transformers":
        "Library of thousands of pre-trained NLP, vision, and audio models with a unified API — for ML researchers and engineers",
    "langchain-ai/langchain":
        "Framework for building LLM-powered applications with chains, agents, retrieval, and tool integrations — for developers building AI applications",
    "hwchase17/langchain":
        "Framework for building LLM-powered applications with chains, agents, retrieval, and tool integrations — for developers building AI applications",
    "ollama/ollama":
        "Run Llama 3, Mistral, Gemma, and other open-weight LLMs locally with a simple CLI and REST API — for developers wanting private, offline AI inference",
    "ggerganov/llama.cpp":
        "High-performance inference engine for LLaMA and other models in C++ with quantization support — for developers running LLMs on consumer hardware",
    "oobabooga/text-generation-webui":
        "Versatile browser UI for running and chatting with local LLMs including LLaMA, Mistral, and RWKV — for AI enthusiasts and researchers using local models",
    "Stability-AI/stablediffusion":
        "Official Stable Diffusion latent diffusion model implementation by Stability AI — for ML researchers experimenting with diffusion models",
    "harry0703/MoneyPrinterTurbo":
        "One-click AI pipeline: LLM script writing → TTS voiceover → auto-subtitles → rendered short video — for content creators automating faceless video channels",
    "open-webui/open-webui":
        "Self-hosted ChatGPT-like UI for Ollama, OpenAI, and other LLM backends with RAG and multi-user support — for teams deploying private AI assistants",
    "binary-husky/gpt_academic":
        "GPT-powered academic assistant for code review, paper reading, LaTeX editing, and translation — for researchers and academics",
    "Yidadaa/ChatGPT-Next-Web":
        "One-click deployable, cross-platform ChatGPT web interface with custom system prompts and multi-model support — for individuals and teams",
    "mckaywrigley/chatbot-ui":
        "Open-source chat interface that works with OpenAI, Anthropic, Google, and local models — for developers building or self-hosting AI chat apps",
    "lobehub/lobe-chat":
        "Modern, extensible AI chat framework with plugin ecosystem, vision, and multi-model support — for teams building AI productivity tools",
    "f/awesome-chatgpt-prompts":
        "Curated collection of effective ChatGPT prompts for dozens of roles and use cases — for users and developers learning prompt engineering",
    "lencx/ChatGPT":
        "Unofficial desktop app wrapping ChatGPT with system tray, keyboard shortcuts, and export — for power users wanting a native ChatGPT experience",
    "deepseek-ai/DeepSeek-Coder":
        "Code-specialised LLM family trained on 2T tokens for completion, generation, and instruction following — for developers and researchers",
    "Mintplex-Labs/anything-llm":
        "All-in-one desktop AI workspace with RAG, agents, custom models, and multi-user support — for teams wanting a self-hosted private AI assistant",
    "BerriAI/litellm":
        "Unified Python SDK and proxy supporting 100+ LLM providers through a single OpenAI-compatible API — for developers switching between or testing AI models",
    "geekan/MetaGPT":
        "Multi-agent framework assigning LLMs to software company roles (PM, engineer, QA) — for developers automating end-to-end software workflows with AI",
    "assafelovic/gpt-researcher":
        "Autonomous research agent that crawls the web and produces structured reports with citations — for professionals needing AI-powered in-depth research",
    "stanford-oval/storm":
        "LLM system that researches a topic and writes a Wikipedia-length structured article with citations — for writers, students, and knowledge workers",
    "vllm-project/vllm":
        "High-throughput LLM inference engine using PagedAttention for fast, memory-efficient serving — for ML engineers deploying LLMs in production",
    "crewAIInc/crewAI":
        "Role-based multi-agent orchestration framework where LLM agents collaborate on complex tasks — for developers building autonomous AI pipelines",
    "crewAIInc/crewAI-examples":
        "Example projects demonstrating CrewAI multi-agent workflows for common automation use cases — for developers learning to build AI agent systems",
    "microsoft/autogen":
        "Conversational multi-agent framework where LLMs collaborate through structured dialogue — for developers building complex autonomous agent systems",
    "phidatahq/phidata":
        "Framework for building multi-modal AI agents with memory, knowledge bases, and tool-calling — for developers creating AI assistants and copilots",
    "mudler/LocalAI":
        "Self-hosted, OpenAI-compatible REST API for running LLMs, image, audio, and TTS models locally — for developers wanting privacy-first AI without cloud APIs",
    "chatchat-space/Langchain-Chatchat":
        "Local knowledge base Q&A system built on LangChain for private document retrieval — for enterprises building internal AI assistants",
    "nomic-ai/gpt4all":
        "Run powerful quantized LLMs locally on CPU with no GPU required — for users wanting private offline AI assistance",
    "jerryjliu/llama_index":
        "Data framework for connecting LLMs to 150+ data sources, building RAG pipelines, and agentic workflows — for developers building knowledge-aware AI apps",
    "run-llama/llama_index":
        "Data framework connecting LLMs to external data sources with 150+ connectors for RAG and agents — for developers building AI apps over private data",
    "facebookresearch/llama":
        "Official LLaMA model weights and reference inference code from Meta AI — for ML researchers and developers working with open-weight LLMs",
    "ShishirPatil/gorilla":
        "LLM fine-tuned to generate accurate API calls across 1,600+ real-world APIs — for developers building tool-calling AI applications",
    "hpcaitech/ColossalAI":
        "Distributed training framework for large models with memory and throughput optimizations — for ML teams training billion-parameter models",
    "tatsu-lab/stanford_alpaca":
        "Dataset and training code for fine-tuning LLaMA into an instruction-following assistant — for ML researchers studying instruction tuning",
    "Vision-CAIR/MiniGPT-4":
        "Multimodal LLM combining Vicuna and BLIP-2 for visual understanding and image-text chat — for researchers in vision-language models",
    "haotian-liu/LLaVA":
        "Visual instruction-tuned multimodal LLM for image understanding and visual question answering — for ML researchers and developers",
    "karpathy/nanoGPT":
        "Minimal, readable implementation of GPT-2 training and fine-tuning in ~300 lines — for ML students and researchers learning transformer architectures",
    "karpathy/minGPT":
        "Minimal GPT implementation in PyTorch for educational purposes — for ML learners studying how autoregressive transformers work",
    "Shubhamsaboo/awesome-llm-apps":
        "Curated examples of LLM apps with RAG, agents, and tool use built on popular frameworks — for developers learning to build AI-powered applications",
    "roboflow/supervision":
        "Computer vision toolkit for detection, segmentation, classification, and annotation — for developers building vision AI applications",
    "agentscope-ai/agentscope":
        "Multi-agent framework with visual monitoring, debugging, and flexible communication patterns — for developers building transparent, trustworthy AI agents",

    # ── Audio & Voice ────────────────────────────────────────────────────────
    "suno-ai/bark":
        "Transformer-based text-to-audio model generating realistic speech, music, and sound effects — for developers building expressive voice applications",
    "coqui-ai/TTS":
        "Deep learning toolkit for text-to-speech with 1,100+ pre-trained models and voice cloning — for developers building multilingual speech synthesis",
    "RVC-Boss/GPT-SoVITS":
        "Few-shot voice cloning and TTS system requiring only 1 minute of reference audio — for content creators and developers building custom voice synthesis",
    "DrewThomasson/ebook2audiobook":
        "Convert ebooks to audiobooks with chapter structure using Calibre and Coqui TTS — for avid readers who prefer listening to books",

    # ── Data & Analytics ─────────────────────────────────────────────────────
    "pathwaycom/pathway":
        "Python streaming data framework for real-time analytics, LLM pipelines, and ETL — for data engineers building live data applications",
    "apache/airflow":
        "Platform for authoring, scheduling, and monitoring data pipelines as code — for data engineers orchestrating complex workflows",
    "dbt-labs/dbt-core":
        "Transformation tool that lets data teams write analytics code in SQL with testing and documentation — for analytics engineers",
    "milvus-io/milvus":
        "Cloud-native vector database for billion-scale similarity search and embedding retrieval — for AI teams building semantic search and RAG systems",
    "qdrant/qdrant":
        "High-performance vector search engine with filtering, payload indexing, and cloud deployment — for developers building AI-powered search and recommendation",
    "chroma-db/chroma":
        "Open-source embedding database for storing, querying, and filtering vector embeddings — for developers building RAG and LLM applications",
    "mindsdb/mindsdb":
        "AI layer for databases that enables ML predictions and LLM queries using SQL — for data teams adding AI to their existing database workflows",

    # ── Security ─────────────────────────────────────────────────────────────
    "projectdiscovery/nuclei-templates":
        "Community-maintained vulnerability detection templates for the Nuclei scanner covering CVEs, misconfigs, and exposures — for security engineers and bug bounty hunters",
    "projectdiscovery/nuclei":
        "Fast, template-based vulnerability scanner for web, network, DNS, and cloud targets — for security professionals and penetration testers",
    "swisskyrepo/PayloadsAllTheThings":
        "Comprehensive payload collection and bypass techniques for web application security testing — for penetration testers and bug bounty hunters",
    "danielmiessler/SecLists":
        "Massive wordlist collection for usernames, passwords, URLs, and fuzzing in security assessments — an essential resource for security testers",
    "trimstray/the-book-of-secret-knowledge":
        "Curated lists of manuals, cheatsheets, one-liners, and tools for sysadmins, network engineers, and security practitioners — for IT professionals",
    "OWASP/CheatSheetSeries":
        "Concise security guidance from OWASP on authentication, injection, cryptography, and 50+ other web security topics — for developers building secure apps",
    "sektioneins/pcc":
        "PHP security toolkit and scanner — for security researchers auditing PHP web applications",
    "mukul975/Anthropic-Cybersecurity-Skills":
        "754 structured cybersecurity skills for AI agents, mapped to MITRE ATT&CK, NIST CSF 2.0, D3FEND, and ATLAS — for AI security tool developers",

    # ── DevTools ─────────────────────────────────────────────────────────────
    "ohmyzsh/ohmyzsh":
        "Community-driven Zsh configuration framework with 300+ plugins and 150+ themes — for developers who live in the terminal",
    "jlevy/the-art-of-command-line":
        "Comprehensive guide to command-line productivity across Linux, macOS, and Windows — for developers and sysadmins",
    "github/gitignore":
        "Official collection of .gitignore templates for every major language and framework — for developers setting up new projects",
    "nicklockwood/SwiftFormat":
        "Command-line tool and Xcode extension for automatically formatting Swift code — for iOS and macOS developers",
    "usebruno/bruno":
        "Offline-first, Git-friendly API client for testing REST, GraphQL, and SOAP — a fast, privacy-respecting Postman alternative for developers",
    "grafana/mcp-grafana":
        "MCP server connecting Grafana dashboards and metrics to AI agents and LLM tools — for DevOps teams integrating AI into observability workflows",
    "gravitational/teleport":
        "Identity-aware access proxy for SSH, Kubernetes, databases, and web apps with auditability — for security-conscious DevOps and platform teams",
    "glanceapp/glance":
        "Self-hosted personal dashboard aggregating RSS, GitHub, stocks, weather, and more — for developers and power users who want a home page",
    "sigstore/cosign":
        "Container image and artifact signing and verification tool — for DevOps teams implementing software supply chain security",
    "argoproj/argo-workflows":
        "Kubernetes-native workflow engine for running parallel data and ML pipelines — for data engineers and platform teams using Kubernetes",
    "kubernetes/minikube":
        "Local Kubernetes cluster for development and testing on any OS — for developers learning or building with Kubernetes",

    # ── Learning & Resources ─────────────────────────────────────────────────
    "donnemartin/system-design-primer":
        "Comprehensive guide to scalable distributed system design with diagrams and Anki flashcards — for engineers preparing for system design interviews",
    "trekhleb/javascript-algorithms":
        "Algorithms and data structures implemented in JavaScript with Big-O complexity analysis — for developers studying CS fundamentals or preparing for interviews",
    "Asabeneh/30-Days-Of-JavaScript":
        "30-day progressive JavaScript challenge from complete beginner to advanced topics — for developers starting their JavaScript journey",
    "microsoft/Web-Dev-For-Beginners":
        "24-lesson, project-based web development curriculum covering HTML, CSS, and JavaScript — for absolute beginners entering frontend development",
    "jwasham/coding-interview-university":
        "Complete, months-long self-study plan covering CS fundamentals needed for software engineering interviews — for developers targeting FAANG-tier companies",
    "EbookFoundation/free-programming-books":
        "Massive multilingual directory of freely available programming books, courses, and podcasts — for developers learning any technology on a budget",
    "kamranahmedse/developer-roadmap":
        "Interactive, opinionated learning roadmaps for frontend, backend, DevOps, and 20+ specializations — for developers planning their career path",
    "TheAlgorithms/Python":
        "All major algorithms and data structures implemented in Python with tests — for students and developers learning algorithms or practicing interview problems",
    "TheAlgorithms/JavaScript":
        "Algorithms and data structures implemented in JavaScript with explanations — for developers studying CS fundamentals",
    "MunGell/awesome-for-beginners":
        "Curated list of open-source projects with beginner-friendly issues across all languages — for new developers making their first open-source contributions",
    "sindresorhus/awesome":
        "The original meta-list linking to hundreds of curated awesome lists across every technology — for developers discovering community resources",
    "labuladong/fucking-algorithm":
        "Systematic LeetCode problem-solving guide with pattern recognition and code templates — for developers preparing for coding interviews",
    "byoungd/English-level-up-tips":
        "Practical, opinionated guide to improving English reading, writing, listening, and speaking for developers — for non-native English speakers in tech",
    "liyupi/ai-guide":
        "Comprehensive Chinese-language guide to AI tools, LLMs, MCP, prompt engineering, and AI-assisted coding — for Chinese developers entering the AI era",
    "rohitg00/ai-engineering-from-scratch":
        "Hands-on AI engineering curriculum from fundamentals to shipping production AI systems — for developers transitioning into AI engineering",
    "hardikpandya/stop-slop":
        "Skill file with rules for removing AI writing clichés and generic filler phrases from generated prose — for writers and editors using AI assistance",
    "harvard-edge/cs249r_book":
        "Open textbook on machine learning systems: deployment, optimization, and hardware for real-world ML — for students and practitioners in applied ML",

    # ── Self-hosted ───────────────────────────────────────────────────────────
    "louislam/uptime-kuma":
        "Self-hosted uptime monitoring tool with status pages and notifications for dozens of channels — for sysadmins and developers monitoring their services",
    "paperless-ngx/paperless-ngx":
        "Community-supported document management system with OCR, tagging, and full-text search — for households and offices going paperless",
    "home-assistant/core":
        "Open-source home automation platform with local control for 3,000+ smart home devices — for home automation enthusiasts who value privacy over cloud dependency",
    "yt-dlp/yt-dlp":
        "Feature-rich fork of youtube-dl supporting 1,800+ sites with faster downloads and active development — for users archiving and downloading online video",
    "Koenkk/zigbee2mqtt":
        "Bridges Zigbee devices to MQTT without vendor hubs, supporting 2,500+ devices — for DIY home automation builders",
    "nextcloud/server":
        "Self-hosted file sync and collaboration platform — for individuals and organizations wanting a private alternative to Google Drive or Dropbox",
    "pi-hole/pi-hole":
        "Network-wide DNS ad blocker running on Raspberry Pi that blocks ads on all devices — for home network administrators",
    "DigitalPlatDev/FreeDomain":
        "Free subdomain and custom domain registration platform — for developers and students who need a domain without a hosting budget",

    # ── Automation & Bots ────────────────────────────────────────────────────
    "n8n-io/n8n":
        "Fair-code workflow automation platform with 500+ integrations, visual editor, and AI agent support — for teams automating business processes without writing full code",
    "unclecode/crawl4ai":
        "LLM-optimized web crawler that outputs clean markdown and structured data from any website — for developers building RAG pipelines and AI datasets",
    "microsoft/playwright":
        "Cross-browser automation library with auto-wait, tracing, and network interception — for developers writing reliable end-to-end tests",
    "selenium/selenium":
        "Industry-standard browser automation framework supporting Python, Java, JS, and more — for QA engineers and developers writing web automation",
    "WhiskeySockets/Baileys":
        "Full-featured WhatsApp Web reverse-engineered API for Node.js — for developers building WhatsApp bots and messaging integrations",
    "dograh-hq/dograh":
        "Open-source voice AI platform with visual workflow builder, MCP support, and telephony — a self-hosted alternative to Vapi and Retell for voice AI developers",

    # ── Data Collection & APIs ───────────────────────────────────────────────
    "public-apis/public-apis":
        "Curated directory of 1,400+ free public APIs spanning weather, finance, sports, government, and more — for developers sourcing data for their projects",
    "iptv-org/iptv":
        "Collection of 8,000+ publicly available IPTV streams from 200+ countries in M3U format — for developers building IPTV apps and cord-cutters",

    # ── JavaScript ecosystem ──────────────────────────────────────────────────
    "mrdoob/three.js":
        "Lightweight WebGL 3D library for rendering scenes, animations, and data visualizations in the browser — for developers building 3D web experiences",
    "chartjs/Chart.js":
        "Simple, flexible canvas-based charting library with 8 chart types and a plugin system — for developers adding charts to web applications",
    "d3/d3":
        "Data-driven SVG, Canvas, and HTML manipulation library for bespoke interactive visualizations — for data journalists and visualization engineers",
    "greensock/GSAP":
        "High-performance JavaScript animation library for complex timeline-based animations — for frontend developers and creative coders",
    "axios/axios":
        "Promise-based HTTP client for browser and Node.js with interceptors and automatic JSON handling — for JavaScript developers making API requests",
    "poteto/hiring-without-whiteboards":
        "Curated list of companies using practical interviews instead of whiteboard algorithm questions — for developers seeking fairer hiring processes",
    "Snailclimb/JavaGuide":
        "Comprehensive Java interview guide covering core Java, Spring, databases, distributed systems, and AI integration — for Java developers and backend engineers",

    # ── Games & Creative ──────────────────────────────────────────────────────
    "zarazhangrui/frontend-slides":
        "Tool for creating animated, code-driven presentation slides using web frontend technologies — for developers and designers who prefer code over PowerPoint",
    "moeru-ai/airi":
        "Self-hosted AI companion with real-time voice chat, personality, and gaming capabilities — for VTubers, streamers, and AI personality enthusiasts",

    # ── Business & Productivity ───────────────────────────────────────────────
    "twentyhq/twenty":
        "Open-source CRM designed for AI-native workflows, self-hostable as a Salesforce alternative — for startups and teams who want full ownership of their customer data",
    "atlassian/atlassian-mcp-server":
        "Official MCP server connecting Jira and Confluence to LLMs, AI IDEs, and agent platforms — for engineering teams integrating project management with AI tools",

    # ── Infrastructure & Cloud ───────────────────────────────────────────────
    "GoogleCloudPlatform/microservices-demo":
        "10-service sample e-commerce app demonstrating Kubernetes, Istio, and gRPC best practices — for developers learning cloud-native architecture",
    "golang-migrate/migrate":
        "Database migration CLI and library supporting 20+ databases — for Go developers managing SQL schema changes",
    "seaweedfs/seaweedfs":
        "Distributed object storage system handling billions of files with O(1) disk access — for teams building scalable file storage infrastructure",
    "gohugoio/hugo":
        "The world's fastest static site generator with themes, multilingual support, and instant rebuilds — for developers and bloggers building static websites",
    "maximhq/bifrost":
        "Enterprise AI gateway supporting 1,000+ models with adaptive load balancing and sub-millisecond overhead — for platform teams managing multi-model AI infrastructure",
    "QuantumNous/new-api":
        "Unified AI model aggregation hub that converts any LLM provider to OpenAI/Claude/Gemini-compatible formats — for developers managing multiple AI API providers",
    "Infisical/agent-vault":
        "HTTP credential proxy and secret manager for AI agents, preventing direct secret exposure — for security teams governing AI agent access to credentials",
    "kubernetes-sigs/agent-sandbox":
        "Kubernetes sidecar pattern for running isolated, stateful AI agent workloads — for platform teams deploying AI agents at scale",
    "iii-hq/iii":
        "Real-time service composition and observability platform for composing, extending, and monitoring microservices — for platform engineers",
    "bia-pain-bache/BPB-Wizard":
        "Deployment wizard for BPB proxy panel management on Cloudflare Workers — for technical users self-hosting privacy proxy tools",
    "james-6-23/codex2api":
        "Reverse proxy and management dashboard for Codex CLI, exposing it as an OpenAI-compatible API — for developers integrating Codex into their toolchain",

    # ── Claude Code / AI Dev Tools ────────────────────────────────────────────
    "anthropics/knowledge-work-plugins":
        "Official Anthropic plugin library for knowledge workers in Claude Cowork — for professionals extending Claude's capabilities with domain-specific tools",
    "anthropics/skills":
        "Public repository of agent skills and capabilities for Claude-based AI agents — for developers building on the Claude agent ecosystem",
    "obra/superpowers":
        "Agentic skills framework and software development methodology for AI coding agents — for engineering teams augmenting their workflow with autonomous AI agents",
    "affaan-m/ECC":
        "Agent harness performance optimization system with skills, instincts, and memory for Claude Code, Cursor, and Codex — for developers maximizing AI IDE productivity",
    "Leonxlnx/taste-skill":
        "AI output quality enforcer that prevents generic, bland LLM responses — for developers and writers who demand consistent, high-quality AI output",
    "Chachamaru127/claude-code-harness":
        "Autonomous Plan → Work → Review development cycle harness for Claude Code — for software teams using AI for high-quality autonomous development",
    "github/awesome-copilot":
        "Curated instructions, prompts, and configuration files for getting the most out of GitHub Copilot — for developers using Copilot in their daily workflow",
    "microsoft/agent-governance-toolkit":
        "Policy enforcement, zero-trust identity, and sandboxing toolkit for autonomous AI agents — for enterprise security teams governing AI agent deployments",

    # ── Crypto / Web3 ────────────────────────────────────────────────────────
    "OpenZeppelin/openzeppelin-contracts":
        "Audited, community-vetted Solidity smart contract library for tokens, access control, and governance — for Solidity developers building DeFi and Web3 applications",
    "MHSanaei/3x-ui":
        "Xray-based multi-protocol proxy panel with traffic limits, multi-user management, and expiry control — for VPN service operators",

    # ── Misc popular ─────────────────────────────────────────────────────────
    "Axorax/awesome-free-apps":
        "Curated list of the best free applications for Windows and mobile — for users and developers discovering quality free software",
    "shiyu-coder/Kronos":
        "Foundation model trained on financial market language for time-series forecasting and market analysis — for quantitative analysts and fintech developers",
    "liyupi/ai-guide":
        "Comprehensive AI learning guide covering LLMs, agents, MCP, vibe coding, and AI-assisted development tools — for Chinese-speaking developers entering AI engineering",
    "signerlabs/ShipSwift":
        "AI-native SwiftUI component library with MCP integration for instant UI generation — for iOS developers accelerating SwiftUI development with AI",
    "zai-org/GLM-OCR":
        "Accurate, fast, and comprehensive OCR system based on the GLM model — for developers building document processing and text extraction pipelines",
    "p-e-w/heretic":
        "Automatic tool for removing safety filters and content restrictions from local language models — for researchers and developers studying model behavior",
    "dograh-hq/dograh":
        "Open-source voice AI platform with MCP support and telephony — a self-hosted alternative to Vapi/Retell for building voice AI applications",
    "james-6-23/codex2api":
        "Go-based reverse proxy turning Codex CLI into an OpenAI-compatible API with a React management dashboard — for developers integrating Codex programmatically",
}

# ── audience suffix by category ───────────────────────────────────────────────
AUDIENCE = {
    "Agentic AI":        "for developers building autonomous AI agent pipelines and multi-agent systems",
    "LLMs & Models":     "for developers and researchers working with large language models",
    "Image & Video":     "for AI artists, content creators, and developers working on generative media",
    "Audio & Voice":     "for developers building voice, transcription, or audio applications",
    "Data & Analytics":  "for data engineers, analysts, and data scientists",
    "Security":          "for security researchers, penetration testers, and defensive security teams",
    "Games & Creative":  "for game developers and creative technologists",
    "Self-hosted":       "for developers and sysadmins running self-hosted infrastructure",
    "Automation & Bots": "for developers automating workflows, processes, and repetitive tasks",
    "Learning":          "for developers learning to code or preparing for technical interviews",
    "DevTools":          "for software engineers and DevOps teams",
    "Web & APIs":        "for developers building web applications and REST or GraphQL APIs",
    "Other":             "for developers",
}

# ── text cleaning ─────────────────────────────────────────────────────────────
_URL  = re.compile(r'https?://\S+')
_JUNK = re.compile(r'[^\x20-\x7eÀ-ɏ‐-‧]+')  # drop non-latin + stray emoji
_WS   = re.compile(r'\s{2,}')

def clean(text: str) -> str:
    text = _URL.sub('', text)
    text = _JUNK.sub(' ', text)
    text = _WS.sub(' ', text).strip().rstrip('.,;:')
    return text

# ── description builder ───────────────────────────────────────────────────────
def build_desc(repo: dict) -> str:
    name  = repo["name"]
    cat   = repo.get("category", "Other")
    raw   = repo.get("desc") or ""

    # 1 — curated override
    if name in KNOWN:
        return KNOWN[name]

    base = clean(raw)
    audience = AUDIENCE.get(cat, "for developers")

    # 2 — decent existing description: append audience
    if len(base) >= 25:
        sep = " —" if not base.endswith(('.', '!', '?')) else " —"
        return f"{base}{sep} {audience}"

    # 3 — short description: combine with audience
    if base:
        return f"{base} — {audience}"

    # 4 — empty: derive readable label from repo slug + category
    slug  = name.split('/')[-1]
    label = re.sub(r'[-_.]', ' ', slug).title()
    return f"{label} — {audience}"

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"Reading  : {SRC.name}")
    repos = json.loads(SRC.read_text(encoding="utf-8"))
    print(f"Repos    : {len(repos):,}")

    curated = improved = fallback = empty_fill = 0
    for r in repos:
        original = r.get("desc") or ""
        r["desc"] = build_desc(r)
        if r["name"] in KNOWN:
            curated += 1
        elif len(clean(original)) >= 25:
            improved += 1
        elif clean(original):
            improved += 1
        else:
            empty_fill += 1

    OUT.write_text(json.dumps(repos, ensure_ascii=False, indent=2), encoding="utf-8")
    size_kb = OUT.stat().st_size // 1024
    print(f"Saved    : {OUT.name}  ({size_kb} KB)")
    print(f"  Curated (known repos) : {curated:,}")
    print(f"  Rule-enriched         : {improved:,}")
    print(f"  Fallback (was empty)  : {empty_fill:,}")

    # Sanity check: spot-check 3 famous repos
    repo_map = {r["name"]: r for r in repos}
    for check in ["vercel/next.js", "open-webui/open-webui", "home-assistant/core"]:
        if check in repo_map:
            print(f"\n  {check}:\n    {repo_map[check]['desc']}")

if __name__ == "__main__":
    main()
