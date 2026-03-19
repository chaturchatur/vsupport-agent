---

## type: interview-prep
status: in-progress
tags:
  - job-search
  - interview
  - active-pipeline

# Observe.AI -- AI Agent Engineer

> [!info]
> Tracking file for the Observe.AI interview process. All context, prep notes, and round details live here.
> See also: [[applications]], [[star-analysis]], [[Resume_MLE.pdf]]

## Role Details

- **Title:** AI Agent Engineer
- **Company:** [Observe.AI](https://www.observe.ai)
- **Location:** Redwood City, CA (Hybrid)
- **Salary:** $108K - $170K + equity
- **Resume submitted:** MLE version
- **Date applied:** 2026-03-13
- **Source:** LinkedIn outreach to Nidhin Varghese

## What Observe.AI Does

- AI agent platform for customer experience (CX)
- Deploys voice and chat AI agents to automate customer interactions
- Also builds AI copilots for human agents and 100% interaction analytics
- Customers: DoorDash, Signify Health, Affordable Care, Verida
- Combines speech understanding, workflow automation, enterprise governance

## What the Role Does

- Own the full AI agent lifecycle: build, integrate, test, demo, deploy, optimize
- Client-facing: weekly demos, gather feedback, primary technical contact
- Systems integration: APIs, CRMs, databases, knowledge systems, auth, error handling
- Telephony integration: SIP/CCaaS/PSTN routing, metadata, fallbacks, call quality
- Prompt engineering, workflow building, performance optimization
- Collaborate with product/engineering while independently leading client delivery

## Key Requirements from JD

- 3+ years conversational AI / ML engineering / system integration (stretch for me)
- Prompt engineering, workflow building, API integration, telephony (SIP, Twilio, Amazon Connect)
- LLMs (GPT, Claude, Gemini), vector DBs, orchestration frameworks (LangChain, LlamaIndex)
- RAG, embeddings, evaluation frameworks, fine-tuning, performance optimization
- Python, JavaScript
- Customer-facing comfort: demos, troubleshooting, project updates
- iPaaS experience (n8n, Zapier)
- Telephony: SIP, PSTN protocols

## My Fit (Strengths)

- RAG pipelines: TryEval (LangChain, ChromaDB, GPT-4o), Sail (FAISS, OpenAI)
- Voice AI / Telephony: Meeting Agent (Twilio softphone, WebSocket media pipeline)
- Multi-agent orchestration: Meeting Agent (3 parallel OpenAI agents)
- Evaluation frameworks: TryEval (built the eval suite + synthetic data engine)
- Real-time systems: Nihilent (video pipeline, <200ms latency, WebRTC)
- Customer-facing: TryEval (worked directly with enterprise customers)
- Full-stack delivery: every role has been end-to-end

## My Gaps

- Only ~2 years experience (they want 3+)
- No direct SIP/PSTN/CCaaS experience (only Twilio via Meeting Agent)
- No iPaaS experience (n8n, Zapier)
- No fine-tuning experience in production
- Haven't used LlamaIndex or Amazon Connect

## Contacts

- **Nidhin Varghese (NV)** -- Hiring Manager, "GTM Charge for Agentic AI"
  - LinkedIn: [https://www.linkedin.com/in/nidhin-varghese-nv/](https://www.linkedin.com/in/nidhin-varghese-nv/)
  - Email: [nidhin.varghese@observe.ai](mailto:nidhin.varghese@observe.ai)
  - Notes: Reached out via LinkedIn DM, responded within 1 minute, forwarded resume to Sue same day. Wants to hire ASAP.
- **Sue Kaufman** -- Sr. Talent Business Partner
  - Email: [sue.kaufman@observe.ai](mailto:sue.kaufman@observe.ai)
  - Notes: Scheduled and conducted recruiter screen on 2026-03-13

## Interview Process

### Round 1: Recruiter Screen with Sue Kaufman -- DONE (2026-03-13)

- 15-min video chat
- Basic fit validation, logistics, visa clarification
- Result: Passed, moved to next round

### Round 2: Hiring Manager Interview with NV -- DONE (2026-03-16, 1 PM)

- First real conversation with Nidhin
- NV discussed two possible roles:
  - **Engineering team** -- builds agent creation tools from scratch (code-heavy)
  - **Implementation team** (NV's team) -- uses company-built tools to configure agents for customers (more tool-using, prompting)
- Ritvik positioned himself in the middle: has experience with both, can understand code well and also use tools, interested in either as long as the work drives customer impact
- NV said he'd loop in the engineering lead and get back
- Sue Kaufman followed up same evening (11:30 PM) asking for thoughts and interest level
- Ritvik replied expressing interest in both roles, referencing the two teams, and said he's looking forward to next steps
- **Status:** Passed -- NV wants Ritvik to proceed with assignment for AI Agent Role

### Round 3: Live Presentation -- VoiceAI Agent Build

- Build a VoiceAI agent: inbound claims support assistant for "Observe Insurance"
- Requirements: greeting/auth, claim status lookup, FAQ, escalation, post-call logging
- Two integrations required: read caller data from external source, write interaction logs back
- Deliverables: working agent, demo recording (happy + error path), architecture diagram, technical write-up
- Expected effort: 6-10 hours
- **Already built** -- got early access to the assessment, coded it up on 2026-03-14
- Officially received assignment from Sue on 2026-03-17 (9:38 PM)
- **Format:** Live conversational presentation to panel
- **Panel:** Ira, Christian, Anna, CP, and NV
- **Scheduled:** Thursday 2026-03-20, 3:00 - 4:00 PM PST (1 hour)
- **Deadline:** Submit presentation to Bruce by 12:00 noon PST Thursday
- **Point of contact:** Bruce Hegg (Sue is OOO starting Wed 2026-03-19)
- **TODO:** Finish polishing everything by Wednesday night. Thursday morning = finalize and send to Bruce before noon PST.

### Presentation Strategy -- What to Hit for Each Panelist

> [!important]
> "The presentation should be very conversational" -- Sue's words. Don't over-formalize this. Talk through your build like you're explaining it to coworkers.

#### For CP (Product Manager)
- **Why you made the choices you made** -- don't just show what you built, explain the tradeoffs
- Product thinking: "I chose X over Y because of Z constraint"
- How you'd scope this differently with more time or different requirements
- Show you understand the customer's problem, not just the technical solution
- If you made assumptions about the user journey, call them out explicitly

#### For Anna (Conversation Designer)
- **Edge cases and error handling are everything** -- this is her domain
- What happens when caller auth fails (wrong DOB, wrong policy number)
- How the agent handles unexpected input or off-topic questions
- Escalation flow: when does the agent hand off to a human, and how gracefully
- Recovery from misunderstanding: does the agent just repeat itself or adapt
- Natural language: does the greeting feel human or robotic
- Show both happy path AND error path demos -- she'll notice if you skip the sad path

#### For Christian (AI Agent Engineer -- your peer)
- **Technical depth has to be real** -- he builds voice agents himself (Wolfe project with WebRTC)
- Architecture choices: why this STT/TTS, why this LLM, why this integration pattern
- How you handle state management across the call
- Latency: what's the response time, what did you do to keep it fast
- Code quality: if they ask to see code, it better be clean
- He'll know if you're handwaving on telephony or agent orchestration -- be precise

#### For Ira (Consulting/Methodology background)
- **Process and structure** -- how you approached the problem, not just the output
- Clear architecture diagram that a non-engineer can follow
- How you'd document this for a team or a customer handoff
- Testing: how do you know it works, what did you validate
- If you have metrics (response time, containment rate), surface them

#### For NV (Hiring Manager)
- **Speed, customer impact, and pragmatism** -- his core values
- Lead with metrics and outcomes, not tech
- Show bias toward shipping: "I built the 80% solution first, then iterated"
- Connect your build to Observe.AI's actual product: "This is a smaller version of what your agents do at scale"
- The "observe then automate" philosophy: did you evaluate your agent's performance or just build and hope
- Phased rollout thinking: how would you deploy this to a real customer

#### General Presentation Flow (1 hour, 5 panelists)
1. **30 seconds:** What you built and why (product framing, not tech)
2. **5 minutes:** Live demo -- happy path first, then error/edge cases
3. **5 minutes:** Architecture walkthrough -- diagram, key decisions, tradeoffs
4. **45+ minutes:** Q&A and conversation (this is the real evaluation -- let them drive)

> [!tip]
> Let them ask questions early. Don't hold them off until the end. If someone interrupts with a question, that's a good sign -- engage with it. NV's team values conversation over presentations.

### Round 4: Engineering Round

- Technical deep dive
- Prep needed: system design, coding, agent architecture

### Round 5: Final Alignment with NV

- Last round, culture/alignment check
- Prep needed: have clear "why Observe.AI" and questions about team/roadmap

## Presentation Panel

### Chamath Perera (CP) -- Product Manager
- Principal/Senior Product Manager at Observe.AI
- Previously at [24]7.ai (same as NV)
- Google Cloud Digital Leader certified
- Focus: conversational AI, voice AI agents, contact center solutions
- **Interview lens:** Product-side evaluator. Will care about how you scope work, communicate tradeoffs, and understand the product

### Ana Dippell (Anna) -- Conversation Designer
- AI Agent Experience Designer at Observe.AI
- Career path: Wysdom -> [24]7.ai (Designer -> Senior -> Lead) -> Observe.AI
- Education: McGill University
- **Interview lens:** Designs the conversation flows agents execute. Will scrutinize error paths, escalation logic, and how natural your agent feels. Make unhappy paths airtight

### Christian T. Stephens -- AI Agent Engineer (same role as Ritvik)
- Website: https://cstephens.xyz
- Grinnell College grad (CS + History)
- Previous: QA Engineer Manager at MyBambu, built QA function from scratch, led team of 6
- Projects: Wolfe (voice-based hotel reservation agent with WebRTC), Tickets Please (AI ticket triage), Business Prediction Agent (voice + financial analysis)
- **Interview lens:** Peer evaluation. He's doing the job you're applying for. Will assess whether you can actually build and whether your technical depth is real. His own projects are voice AI -- he'll know if you're handwaving

### Ira Sabnis
- Background: DA & AI Associate at PwC, Georgia Tech grad (Business Admin + IT Management)
- AWS Cloud Practitioner certified
- Interested in conversational AI design
- May have recently joined Observe.AI
- **Interview lens:** Consulting/methodology background. Will evaluate process, documentation, and how you explain your approach

### Nidhin Varghese (NV) -- Hiring Manager
- See NV Deep Dive section below

## Visa / Logistics

- Can start part-time on CPT during spring semester (20 hrs/week max, F1 restriction)
- Full-time available after graduation May 20, 2026
- OPT + STEM extension covers through June 2029, no sponsorship needed for 3 years
- Open to relocating to Redwood City for hybrid

## NV Deep Dive -- Nidhin Varghese Profile

### Career History

- **[24]7.ai** -- 13+ years. Rose to leadership in conversational AI. Led new market expansion, optimized offerings (30% win-loss improvement). Company recognized by Forrester, Quadrant, Opus Research under his leadership.
- **Appen** -- Head of Product Marketing (Jun 2023 - Nov 2023)
- **Truveta** -- Consultant, Product Strategy & Business Ops (Nov 2023 - Apr 2024)
- **Concentrix Catalyst** -- Sr. Director, Solutions Architecture (Apr 2024 - late 2024)
- **Observe.AI** -- Head of AI Agent Practice, Solutions Consulting & Implementation (joined ~Dec 2024)

### Education

- BE in Mechanical Engineering, Anna University Chennai

### Self-Description

- "Conversational AI SME by profession, strategist by instinct, people-first innovator who turns AI ambition into action"
- Specializes in orchestrating high-stakes POCs, fine-tuning automation frameworks, leading charge on agentic AI

### Key Insight

- NV is NOT an engineer by current function. He's a GTM/solutions leader who hires engineers to build what he sells to customers. 13 years at [24]7.ai means he's deeply experienced in conversational AI from the business/delivery side.

### What He Values (from LinkedIn posts)

1. **"Perfectionism kills momentum; iteration builds trust"** -- ship fast, learn in production
2. **Phased rollouts** -- not big-bang launches. Dental clinic deployment: Day 1: 30 min observation, Day 2: 60 min, Days 3-4: 4-hour windows
3. **Real metrics over demos** -- every post includes concrete numbers (40% voicemail reduction, 1.5 min saved per call, ~2 hours/agent/week)
4. **Partial automation is fine** -- target high-friction steps first, don't need end-to-end automation to deliver value
5. **Pragmatic workarounds** -- when APIs weren't ready, used shared docs instead of waiting
6. **Customer wow factor** -- first 2 weeks at Observe.AI he did 9 customer demos

### Notable LinkedIn Posts

- Deployed AI agents across 400+ dental clinics, replacing legacy IVR. Reduced voicemail volume from 40%+ to near zero, calls completing in 60-90 seconds
- Healthcare insurance broker: AI agent handles caller verification (DOB, ZIP, last-four SSN), saves ~2 hours/agent/week
- First post at Observe.AI: led 9 customer meetings in 2 weeks, uses "AI Agent Readiness Rubric" to assess customer readiness

### Interview Implications

- He values speed, directness, and people who ship
- Lead with real metrics and customer impact, not just tech
- Show you're comfortable iterating in production
- Frame TryEval as "evaluation-first" -- matches Observe.AI's "observe then automate" philosophy
- Own your gaps honestly -- he'll spot BS after 13 years in this space

## Observe.AI -- Company & Product Deep Dive

### Company Stats

- Founded ~2017, 7 years old
- $214M Series C (2022) at ~$1B valuation
- Backed by SoftBank, Zoom Ventures, Menlo Ventures
- 350+ contact centers deployed
- 65% of workforce in ML/GenAI, 40% YoY R&D headcount growth
- 25 published research papers
- IDC MarketScape Leader (2025-2026)
- H1 FY2024: 155% increase in net new bookings, 193% enterprise segment growth, 33% more agents on platform

### Product: Three Pillars

1. **VoiceAI Agents** -- autonomous voice bots handling inbound/outbound calls
2. **Real-Time Agent Assist** -- copilot for human agents during live calls
3. **AutoQA + Interaction Analytics** -- post-call scoring of 100% of conversations, coaching, insights

### VoiceAI Agents -- How It Works

- Inbound call hits telephony layer (SIP trunk / CCaaS integration)
- Real-time STT transcribes caller speech (proprietary contact center ASR)
- LLM-based dialogue engine processes intent, maintains state, executes workflows
- TTS renders agent responses back to caller
- Integrations fire in real-time (CRM lookups, ticket creation, escalation)
- Post-call: interaction logged, AutoQA evaluates, insights surface in dashboard
- 200+ out-of-the-box integrations
- 1 week to production (vs months for legacy)
- 95% containment rate (Affordable Care case study)
- Enterprise security: GDPR, HIPAA, HITRUST, SOC2, ISO27001

### Tech Stack (from JD + engineering signals)


| Component         | Details                                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------------- |
| **STT**           | Proprietary contact center ASR (their original product), possibly augmented with Deepgram/Whisper |
| **TTS**           | Not disclosed. Likely ElevenLabs, PlayHT, Cartesia, or Azure Neural TTS                           |
| **LLM**           | Model-agnostic: GPT-4/4o, Claude, Gemini. Proprietary contact center LLM for analytics            |
| **Orchestration** | LangChain, LlamaIndex for RAG/agent workflows                                                     |
| **Vector DB**     | Not disclosed. Likely Pinecone, Weaviate, or ChromaDB                                             |
| **Languages**     | Python (ML/AI), JavaScript/TypeScript (frontend, integrations)                                    |
| **Infra**         | AWS, Kubernetes                                                                                   |
| **Telephony**     | SIP trunking, CCaaS integrations (Amazon Connect, Genesys, Five9, NICE, Talkdesk, Twilio)         |


### Competitive Positioning


| Competitor           | How Observe.AI Differs                                                                               |
| -------------------- | ---------------------------------------------------------------------------------------------------- |
| **Retell AI / VAPI** | Developer API tools. Observe.AI is enterprise platform with full analytics + agents + copilot        |
| **LiveKit**          | Real-time infra (WebRTC). Building block, not competitor. Observe.AI might use it under the hood     |
| **Bland AI**         | Outbound calling focus. Observe.AI is broader: inbound + outbound + analytics + copilot              |
| **Cresta**           | Closest competitor. Real-time coaching + analytics. Observe.AI differentiates with autonomous agents |
| **Dialpad / Gong**   | Adjacent -- conversation intelligence, not autonomous agents                                         |


### The Moat: "Observe, Then Automate"

- Started by analyzing 100% of human agent calls, learning what "good" looks like
- Then built AI agents to replicate the best human agent behaviors
- AutoQA evaluates AI agents using the same framework as human agents
- This closed loop (agent + evaluation + optimization) is unique -- competitors are point solutions

## Resume Question Prep for NV Interview

### Questions to Nail

**"Walk me through Meeting Agent"** -- money project for this role

- Why Twilio, how WebSocket media pipeline works, parallel agent orchestration, latency challenges
- Connect: "This is a smaller version of what Observe.AI builds at scale"

**"Tell me about your RAG experience"** -- lead with TryEval (enterprise, customer-facing)

- Chunking strategy, embedding choices, retrieval quality, evaluation
- Connect: their agents need knowledge bases for FAQ handling

**"You have ~2 years, role asks for 3+. Why you?"**

- Don't be defensive. Density of relevant work is high
- Voice AI, RAG, multi-agent, real-time pipelines, customer-facing delivery, full stack

**"Customer-facing experience?"**

- TryEval: enterprise customers, shipped eval suite they used directly (2h to 5min)
- Nihilent: built analytics dashboard for Emoscape tool

**"Real-time systems / latency?"**

- Nihilent: <200ms video pipeline, WebRTC, async Redis queues
- Meeting Agent: WebSocket media pipeline, live transcription

### Gaps to Own Honestly

**SIP/PSTN/CCaaS** -- no direct experience, but used Twilio (abstracts those protocols). Can learn fast.

**iPaaS (n8n, Zapier)** -- haven't used, but built custom integrations (Jira API, multiple data source APIs). Can pick up workflow builders quickly.

**Fine-tuning** -- not in production. But deployed ML at Nihilent and LLMs at CapX/TryEval.

### Questions to Ask NV

- "When you deployed across 400+ dental clinics, how did you handle variance in each clinic's workflow?"
- "What does the AI Agent Readiness Rubric look like? How do you assess customer readiness?"
- "What's the typical ramp -- am I working on one client deployment or multiple in parallel?"
- "What's the current stack for voice agents -- own STT/TTS or third-party?"
- "How do you evaluate agent performance in production? What metrics matter most?"
- "What's the biggest technical challenge the team is working on right now?"

### Strategic Framing

- TryEval = "observe then automate" philosophy (evaluation-first, same as Observe.AI's moat)
- Meeting Agent = direct proof you can build voice AI
- Frame everything in terms of customer impact and real metrics, not just tech
- Show bias toward shipping and iterating -- matches NV's values

## LinkedIn Thread Summary (2026-03-13)

- Ritvik reached out to NV about the AI Agent Engineer role
- NV responded immediately, asked for resume via email
- NV asked about sponsorship and full-time vs internship
- Ritvik clarified: no sponsorship needed till 2029, looking for full-time
- NV said he'd review and get back

## Email Thread Summary (2026-03-13)

- Ritvik emailed resume to NV
- Sue Kaufman reached out same day (NV's calendar was full)
- Scheduled and completed 15-min video screen
- Moved to Round 2 with NV on Monday

## Interview Prep

### Stage 1: "About Me" -- Elevator Pitch

> [!note] Delivery target: 60-90 seconds. Direct, metric-driven, no fluff.

**The Pitch:**

"I'm Ritvik -- I build production AI systems that serve real users. I'm finishing my MS in Applied Machine Learning at UMD in May, but most of my learning has been in production, not classrooms.

At TryEval, I built a RAG-powered evaluation platform for enterprise customers -- context creation went from 4 hours to 30 minutes, end-to-end workflows from 2 hours to under 5 minutes. I was the primary technical contact, shipping directly to the people using it.

Before that, at Nihilent, I built a real-time video analysis pipeline -- sub-200ms latency, WebRTC streaming, async Redis queues. That's where I learned what production latency constraints actually feel like.

On my own time, I built Meeting Agent -- a voice AI assistant using Twilio, WebSocket media pipelines, and parallel OpenAI agents for live transcription and task extraction. It's a smaller version of what Observe.AI does at scale, and building it is what made this role click for me.

What draws me to Observe.AI specifically is the 'observe then automate' approach -- you analyzed 100% of human agent calls first, learned what good looks like, then built AI agents to replicate it. That's evaluation-first thinking, which is exactly how I built at TryEval. I don't want to just build agents -- I want to build agents that are measurably better than what they replace.

I'm ready to start part-time on CPT now and go full-time after graduation in May. No sponsorship needed for three years."

**Coaching Notes:**

- **Tone:** Talk like you're explaining to a coworker, not presenting to a panel. NV is casual and direct -- match that energy.
- **Speed:** Don't rush. The metrics speak for themselves -- let them land. Pause after "4 hours to 30 minutes" and "sub-200ms."
- **Don't say:** "project," "academic," "coursework," "I'm just a student." Say "product," "system," "shipped," "deployed."
- **The hook:** The "observe then automate" line connects your TryEval experience directly to their moat. NV lives and breathes this philosophy -- showing you understand it signals you've done your homework.
- **If he asks to go deeper on anything:** That's a win. The pitch is designed to open doors to Meeting Agent, TryEval, or Nihilent -- all three are prepped for Stage 2.
- **Body language:** Lean in slightly, maintain eye contact. NV is a people-first leader -- he's reading your energy as much as your words.

### Stage 2: Resume Deep Dive -- NV-Style Framing

> [!note] For each resume entry: lead with the product, the customer, and the metric. Use NV's language -- "shipped," "deployed," "rolled out." Never "developed as part of coursework."

#### TryEval -- Contract MLE (Dec 2025 - Feb 2026) [MONEY PROJECT]

**Product:** An LLM evaluation platform where enterprise customers needed to stress-test their AI systems before deploying to production.

**Customer pain:** Two core problems:

1. **No good eval datasets** -- customers either used TryEval's generic presets (not specific to their domain) or had to manually create datasets / pull real data from their systems. Neither scaled.
2. **No way to eval against their own knowledge** -- customers wanted datasets generated from their actual policies and knowledge bases so evals would test exactly what the model would face in production.

**NV-style talking points:**

- "I solved two distinct customer problems. First: they needed realistic eval data but didn't have it. I built a synthetic dataset generation engine -- no LLMs, pure NLP augmentation and degradation -- so it was fast, cheap, and hallucination-free. The degradation system emulated real-world data quality issues so the stress tests actually meant something."
- "Second: customers wanted evals grounded in their own knowledge. I built a RAG pipeline that ingested whatever docs the customer provided -- policies, FAQs, knowledge bases -- and tasked an LLM to generate rich base context in small batches (250-300 rows max). Small enough that the LLM produces high-quality data without hallucinating, large enough to seed the synthetic engine."
- "The CEO would talk to customers, come to me with the problem, and I'd ship a solution. Feedback the same week, iterate, make it better. No handoffs, no tickets -- just direct delivery loop between me and the customer's pain."
- "For the eval suite UI, I had to think about different customer types. Some wanted a quick score -- fast/simple mode. Others wanted granular control -- advanced mode. Catering the experience to different user sophistication levels is what made adoption stick."

**Production lesson:** "Evaluation isn't a checkbox -- it's a product. You build the eval system first, then the eval system tells you what to build next. That's the same philosophy Observe.AI uses: observe first, then automate."

**Connect to Observe.AI:** TryEval's eval-first approach mirrors Observe.AI's AutoQA. Both start by defining what "good" looks like before automating. The fast/simple vs advanced mode thinking maps directly to Observe.AI's customer base -- some contact centers want turnkey, others want full control.

---

#### UMD Research -- Grad Research Contributor (Aug 2025 - Dec 2025)

**Product:** A data fusion pipeline for wildfire detection that combines satellite imagery and ground sensors from NASA, ESA, and PurpleAir.

**Customer pain:** Researchers were manually wrangling data in 3 different formats (JSON, CSV, NetCDF) from 3 different agencies. Couldn't get a unified view without weeks of preprocessing.

**NV-style talking points:**

- "I built an ETL pipeline that ingested 10GB+ of multimodal data and normalized it into a single ML-ready schema. The research team went from weeks of preprocessing to a repeatable, containerized workflow."
- "Trained a fusion model that improved prediction accuracy by 12% by calibrating satellite data against ground sensors."
- "Containerized the whole thing in Docker so any team member could reproduce results on any machine."

**Production lesson:** "Real-world data is messy. Three agencies, three formats, different coordinate systems, different time resolutions. You don't get clean data -- you build systems that handle dirty data reliably."

**Connect to Observe.AI:** Data integration across multiple sources -- same challenge when integrating with customer CRMs, telephony systems, and knowledge bases.

---

#### Nihilent -- AI Project Trainee (Jan 2024 - Jul 2024) [MONEY PROJECT]

**Product:** Emoscape -- a real-time sentiment analysis system that processes live video feeds and surfaces audience reaction insights. My ownership was the ingestion pipeline and a demo dashboard.

**Customer pain:** The ML team had a strong model but no production-grade way to feed it video frames at the speed and reliability it needed. Direct preprocessing after ingestion was causing high latency and packet loss.

**NV-style talking points:**

- "I was tasked with building the ingestion pipeline and making it production-grade. The problem was straightforward -- when I preprocessed frames directly after ingestion, latency spiked and packets dropped. So I decoupled them: Redis queues to buffer incoming video frames, Redis workers to preprocess one by one off the queue. That fixed the packet loss and got us sub-200ms end-to-end latency."
- "The architecture pattern is simple but it's the right one -- decouple ingestion from processing so a burst of frames doesn't crash the pipeline. Same pattern you'd use for handling voice streams at scale."
- "I also built a demo dashboard in React/Redux to visualize inference results -- not a production interface, but enough to show the system working end-to-end and get stakeholder buy-in."
- "On the model side, I was shadowing the senior engineers -- attending design meetings, watching how they built and iterated on the CNN-LSTM architecture. I didn't own the model, but I learned how production ML teams think about accuracy vs latency tradeoffs."

**Production lesson:** "The model is only as good as the pipeline feeding it. A 92% F1 model is useless if frames are dropping or arriving late. I learned that production ML is a systems problem first, a modeling problem second."

**If NV asks "What did you learn from shadowing the ML team?"**

- "I saw how they approached the accuracy-latency tradeoff. The CNN handles frame-level features, the LSTM adds temporal context -- you're not just classifying individual frames, you're tracking how reactions change over time. They chose that hybrid specifically because pure CNN was fast but missed temporal patterns, and pure sequence models were too slow for real-time."
- "They weren't chasing state-of-the-art -- they were chasing 'good enough at 200ms.' That's a production mindset, not a research mindset."
- "Biggest takeaway: the senior engineers spent more time on data quality and pipeline reliability than on model architecture. The model was maybe 20% of the conversation. The rest was 'how do we get clean frames in fast enough' -- which was literally my job."

> [!warning] Don't volunteer this unprompted. Only if he digs into the model side.

**Connect to Observe.AI:** The ingestion pipeline pattern -- buffer incoming streams, process asynchronously, maintain latency targets -- is exactly what voice AI agents need. Swap video frames for audio streams and it's the same architecture.

---

#### CapX AI -- SDE Intern (May 2023 - Dec 2023)

**Product:** Two internal tools -- an automated social signal monitoring system and a community support ticketing system for a 65K+ member community.

**Customer pain:** Team was spending 15+ hours/week manually monitoring social signals. Support tickets took 48 hours average to resolve. A 65K-member community was growing faster than the team could handle.

**NV-style talking points:**

- "I automated their social monitoring pipeline and plugged GPT-3.5 into it for context-aware outreach. Saved 15 hours a week -- that's almost two full workdays back."
- "The ticketing system I built cut mean time to resolution from 48 hours to under 10. That's an 80% reduction for a community of 65K people."
- "This was 2023 -- early days for LLMs in production. I was integrating GPT-3.5 into real workflows before most teams had figured out prompt engineering."

**Production lesson:** "Automation doesn't have to be perfect to be valuable. The GPT-3.5 outreach wasn't flawless, but it was 15 hours/week better than doing it by hand. Ship the 80% solution, iterate from there."

**Connect to Observe.AI:** NV's philosophy -- "perfectionism kills momentum; iteration builds trust." CapX is a direct example of shipping partial automation that delivers real value immediately.

---

#### Meeting Agent [MONEY PROJECT -- lead with this]

**Product:** A voice AI meeting assistant that joins calls via Twilio softphone, transcribes in real-time, and runs parallel AI agents for notes, task extraction, and gap analysis.

**Customer pain:** Meeting participants lose track of action items and discussion gaps. Manual note-taking is unreliable and distracting.

**NV-style talking points:**

- "This is the project that connects most directly to what Observe.AI builds. I built a voice AI system with Twilio, WebSocket media pipelines, and real-time transcription -- that's the same architecture stack."
- "I orchestrated three parallel OpenAI agents, each with a different job: one for notes, one for tasks, one for identifying gaps in the discussion. They run concurrently against the same transcript stream."
- "Everything streams live to the UI via Supabase Realtime. You see notes, tasks, and gaps populating as the conversation happens -- not after the call ends."
- "The Twilio integration handles the telephony layer -- media streams over WebSocket, audio processing, connection management. It's not SIP directly, but it's the abstraction layer on top of it."

**Production lesson:** "Voice AI is a systems problem, not a model problem. The model is 20% of it. The other 80% is telephony, streaming, latency, error handling, and making sure the user sees results in real-time."

**Gap to own (SIP/PSTN):** "I built Meeting Agent on Twilio, which abstracts the telephony layer. But I've since gone deeper -- I understand what Twilio is doing under the hood. An incoming call is a SIP INVITE that negotiates codecs and media ports via SDP, the actual voice audio flows on RTP over UDP separately from signaling, and Twilio's SIP trunks connect to upstream carriers handling codec transcoding between G.711 and whatever the client sends. I haven't configured raw SIP trunks or worked directly with an SBC, but I understand the protocol stack and the call flow end-to-end. Going from Twilio's abstraction to working with CCaaS platforms like Amazon Connect or Genesys is learning configuration, not learning concepts."

---

#### TryEval (Evaluation Suite) -- the "observe then automate" bridge

**For when NV asks how your experience connects to Observe.AI's moat:**

"At TryEval, I built the evaluation layer before the automation layer. You define what 'good' looks like with your eval suite, then you build systems that hit those benchmarks. That's exactly what Observe.AI does -- you started with AutoQA analyzing 100% of human calls, learned the patterns, then built AI agents to replicate the best human behaviors. The eval loop isn't a nice-to-have, it's the product."

---

#### Gaps to Own Honestly (NV respects this)

| Gap                           | How to frame it                                                                                                                                                                                                                                                                                                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **~2 years vs 3+ required**   | "My experience is dense. In 2 years I've shipped voice AI, RAG pipelines, real-time systems, and enterprise eval tools -- all end-to-end, all in production. Density matters more than calendar time."                                                                                                                                                                                  |
| **SIP/PSTN/CCaaS**            | Not a gap anymore. "I studied the full protocol stack while building my voice agent -- SIP signaling, RTP media transport, codec negotiation, SBC routing. I used Twilio because it's the right abstraction for a solo project, but I understand what it's doing under the hood."                                                                                                       |
| **iPaaS (n8n, Zapier)**       | "I've used both n8n and Zapier -- experimented with them at CapX when building outreach automation. I'm comfortable with them, but I prefer coding automations in Python or orchestrating with LangChain/LangGraph because it gives me more control and full ownership. If the team uses n8n, I'd use the API to interact with it rather than the UI -- same result, more flexibility." |
| **Fine-tuning in production** | "I have the theoretical foundation from my ML coursework at UMD -- training loops, hyperparameter tuning, evaluation methodology -- plus some production exposure from Nihilent where I worked alongside the ML team on a deployed model. I haven't done a full production fine-tune end-to-end myself, but the base knowledge is there and the gap is execution, not understanding."   |

### Stage 3: Questions NV Might Ask + Questions to Ask NV

> [!note] Trimmed for a 30-minute interview. Only the questions that are actually likely, with concise answer frameworks -- not scripts.

#### Most Likely Questions

**"Tell me about yourself / Walk me through your background"**

- Use the Stage 1 pitch. Under 60 seconds. End with the "observe then automate" hook.

**"Walk me through Meeting Agent"**

- Product: voice AI assistant, Twilio softphone, real-time transcription, parallel agents
- Architecture in one sentence: "Incoming call hits Twilio, audio streams over WebSocket, three parallel OpenAI agents process the transcript for notes, tasks, and gap analysis, results stream live to the UI via Supabase Realtime."
- Why it matters: "It's the same architecture pattern as Observe.AI's voice agents -- telephony layer, media streaming, LLM processing, real-time output. Smaller scale, same paradigm."
- Keep under 2 minutes. Let him ask follow-ups.

**"Tell me about your RAG experience"**

- Lead with TryEval: "Enterprise customers needed eval datasets grounded in their own knowledge. I built a RAG pipeline -- LangChain, ChromaDB, Sentence Transformers -- that ingested their docs and generated base context for the synthetic data engine. Small batches, 250-300 rows, so the LLM produced rich data without hallucinating."
- Connect: "Your agents need knowledge bases for FAQ handling and customer-specific workflows. Same retrieval problem."

**"You have ~2 years, we asked for 3+. Why should we bet on you?"**

- Don't be defensive: "In 2 years I've shipped voice AI, RAG pipelines, real-time systems under 200ms latency, and enterprise eval tools. All end-to-end, all to real users. Density matters more than calendar time."

**"How are you with customer-facing work?"**

- TryEval: "I was the primary technical contact. CEO talked to customers, brought problems to me, I shipped solutions and got feedback the same week. Direct delivery loop."
- Frame: "I'm comfortable presenting, demoing, and troubleshooting directly with customers. I did it at TryEval and I'm excited to do it at Observe.AI."

**"Real-time systems / latency experience?"**

- Nihilent: "Built the video ingestion pipeline for Emoscape. Direct preprocessing was causing packet loss, so I decoupled it -- Redis queues to buffer frames, Redis workers to process. Got sub-200ms latency."
- Meeting Agent: "WebSocket media pipeline for live audio streaming and transcription."
- Connect: "Same patterns voice AI needs -- streaming input, async processing, strict latency targets."

#### Experience Validation Questions (if he probes gaps)

**"SIP/PSTN -- you haven't worked with it directly?"**

- "I built on Twilio for Meeting Agent, but I studied the protocol stack to understand what's underneath -- SIP signaling, RTP for media transport, codec negotiation, SBCs. I used the abstraction because it was the right choice for a solo project. I understand the layers and can work with raw SIP trunking or CCaaS integrations."

**"iPaaS experience?"**

- "I've used n8n and Zapier -- experimented with them at CapX for outreach automation. I'm comfortable with both, but I prefer coding automations in Python or orchestrating with LangChain/LangGraph for more control. If the team uses n8n, I'd use the API rather than the UI."

**"Fine-tuning?"**

- "Theoretical foundation from UMD, some production exposure at Nihilent. Haven't done a full production fine-tune myself. The gap is execution, not understanding."

#### "How Would You Build X" Design Questions

**"How would you build a voice AI agent for inbound claims support?"**

- "I'd start with the call flow: SIP INVITE comes in through the CCaaS platform, AI agent picks up instead of IVR. STT converts caller audio to text, LLM processes intent -- greeting, authentication, claim lookup, FAQ, or escalation. TTS converts response back to audio, streams via RTP."
- "For integrations: real-time CRM lookup for caller data, API call to claims system for status, write interaction logs back after call ends."
- "Evaluation: use AutoQA-style scoring on every interaction. Define what 'good' looks like first, then optimize toward it."
- "Phased rollout: start with a narrow use case (claim status only), measure containment rate, expand."

**"How would you handle a deployment across multiple customer sites with different workflows?"**

- Reference his dental clinics post: "I saw your deployment across 400+ clinics. I'd approach it the same way -- phased rollout, start with observation (Day 1: 30 min), expand gradually, measure at each stage. Each site gets a config layer for their specific workflow, but the core agent logic stays shared."

#### Culture / Speed / Iteration Questions

**"How do you handle ambiguity?"**

- TryEval failure injection: "When I was building the synthetic data engine, there was no existing taxonomy for failure types. I had to define the 5 tiers myself -- from subtle typos to complete semantic corruption. I proposed it, got feedback, iterated. Didn't wait for a perfect spec."

**"Tell me about a time you shipped something fast"**

- "At TryEval the CEO would bring me a customer problem and I'd have a working solution within the week. The RAG context generator went from 'customers are spending 4 hours on this' to 'shipped and deployed' in about a week."

**"Why Observe.AI?"**

- "Three things. First, the 'observe then automate' approach -- you started with analytics on human calls, learned what good looks like, then built AI agents. That's evaluation-first, which is exactly how I think. Second, the closed loop -- agent plus AutoQA plus optimization is a moat that point solutions can't replicate. Third, I want to build voice AI for real customers at scale, not toy demos."

#### Questions to Ask NV (pick 2-3 for a 30-min call)

1. **"When you deployed across 400+ dental clinics, how did you handle variance in each clinic's workflow?"** -- shows you read his posts, asks about a real operational challenge
2. **"What does the AI Agent Readiness Rubric look like? How do you assess whether a customer is ready for AI agents?"** -- shows you understand not every customer is ready, asks about his framework
3. **"What's the typical ramp for this role -- am I working on one client deployment or juggling multiple in parallel?"** -- practical, shows you're thinking about execution

> [!warning] Don't ask more than 3. In a 30-min interview, your questions should take 3-5 minutes max. Let him talk -- his answers will tell you a lot about the role.
