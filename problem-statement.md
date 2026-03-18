Observe.AI – Take-Home Assessment
AI Agent Engineer)
Objective
Demonstrate your ability to design, integrate, and optimize a VoiceAI agent from a
technical and analytical standpoint. This take-home challenge places you in the role of an
AI Agent Engineer. You will design and build a voice-enabled assistant that simulates a
real inbound customer support call. The goal is to evaluate your practical skills in
conversational design, workflow logic, data integration, and overall product reasoning.
Scenario: “AI Claims Support Assistant for Observe Insuranceˮ
You are tasked with building a VoiceAI Agent that handles inbound calls from customers
checking on their insurance claim status. Your AI assistant should support the following
capabilities:

1. Greeting & Authentication: The assistant greets the caller and asks for the phone
   number associated with their account. It uses this number to look up the caller in
   an external data source (e.g., Google Sheets, Notion, Airtable) containing first
   name, last name, phone number and claim status. If the record is found, the
   assistant confirms the identity by asking, “Am I speaking with {first name} {last
   name}?ˮ and continues upon confirmation. If the number does not match a
   record-or the caller denies the identity-the assistant should gracefully attempt
   alternative verification or indicate that a human representative will follow up.
2. Claim Status Handling: After authentication, the assistant retrieves and
   communicates the callerʼs claim status (e.g., approved, pending, or requires
   documentation). If the claim requires documentation, the agent provides clear
   instructions on how to submit it (e.g., upload to the portal or email
   support@observeinsurance.com).
3. FAQ Support: The assistant should be able to answer common questions such as
   office hours, mailing address, how to start a new claim, and the general claims
   handling process. These responses may be supported by a simple internal
   knowledge base.
4. Escalation & Safety Behavior: If the caller requests a representative, the assistant
   should politely confirm that a callback or transfer will be scheduled.If the caller
   indicates an emergency, the assistant should instruct them to hang up and dial 911
   immediately. If the caller asks unrelated questions, the assistant should briefly
   clarify what it is able to help with and guide the conversation back to the task.
5. Call Completion & Summary Logging: At the end of the call, the assistant writes a
   post-call record to an “interactionsˮ table Notion, Google Sheets, AirtabIe)
   including: caller name (if authenticated), summary of the conversation, call
   sentiment (simple: positive / neutral / negative), timestamp
   Throughout the interaction, the assistant should maintain a calm, supportive, and
   conversational tone - accurately interpreting the callerʼs questions and concerns, and
   responding in a clear, reassuring, human-like manner.
   Requirements
6. VoiceAI Agent Build
   ● Use any VoiceAI builder Retell, VAPI, n8n, LiveKit, etc.) or custom
   framework of your choice. Additionally, use any integration platform of your
   choice Firebase Cloud Functions, n8n, Make.com, etc.)
   ○ Your agent must demonstrate two integrations:
   ■ Retrieve caller information and claim status from an external
   system using the callerʼs phone number.
   ■ Write back a post-call interaction record (including caller
   name, summary, sentiment, and timestamp) to an external
   “interactionsˮ table.
   ● Include at least one branching workflow (happy path and error path).
   ● Submit a recording or demo link showing both a “happyˮ and “errorˮ
   interaction. Bonus: You can also provide a working number for us to try it
   out and provide access to any external systems.
7. Solution Architecture Diagram
   a. Provide a conversational flow chart Lucidchart, Draw.io, Figma, etc.) that
   includes:
   ● Voice flow steps (greeting → authentication → API call → response
   handling → fallback)
   ● Integration points APIs, data storage, telephony routing,
   TTS/STT/LLM layers)
   ● Monitoring or logging touchpoints (where errors or metrics are
   captured)
8. Technical Write-Up
   a. Provide an overview of:
   a) Tools, Frameworks, and APIs
   i) Explain your architecture choices STT, TTS, LLM.
   ii) Why did you select those models/tools?
   iii) How would this scale for production?
   b) Problem Solving & Debugging
   i) Describe one technical challenge you encountered while
   building and how you solved it.
   ii) If you had one more week, what would you optimize?
   c) Data & Metrics Evaluation:
   i) Explain how you would measure performance and improve
   ROI over time:
   1 Metrics you would track
   2 How you would use this data to improve agent logic or
   prompt tuning
   3 Provide an example of how youʼd identify and fix a
   drop in containment or increase in average handle
   time.
   Please submit the following deliverables (approximately 610 hours of effort expected
   for this project). Clarity and completeness are key.
