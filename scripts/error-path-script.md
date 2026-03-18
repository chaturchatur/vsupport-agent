# Error Path Demo Scripts

## Scenario A: Identity Denial + Re-verification (Multi-Match)

**Caller profile:** Michael Johnson, phone +14155555678, claim CLM-2024-002 (pending)
**Setup:** Phone matches Sarah Johnson first; caller denies → last_name "Johnson" returns 2 matches → first name disambiguates.

---

### Call Flow

1. **Agent (auto-greeting):**
   > "Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?"

2. **Caller:**
   > "Hi, I'd like to check on my claim."

3. **Agent:**
   > "I'd be happy to help. Could you provide the phone number on your account?"

4. **Caller:**
   > "It's 415-555-5678."

5. **Agent** *(calls `lookup_caller` with phone_number → matches Michael Johnson)*:
   > "Am I speaking with Michael Johnson?"

6. **Caller:**
   > "No, that's not me."

7. **Agent** *(re-verification flow)*:
   > "I apologize for the confusion. Could you please provide your last name so I can look up your account?"

8. **Caller:**
   > "Johnson."

9. **Agent** *(calls `lookup_caller` with last_name="Johnson" → 2 matches: Sarah Johnson + Michael Johnson)*:
   > "I found a few accounts under that name. Could you confirm your first name?"

10. **Caller:**
    > "Michael."

11. **Agent** *(matches Michael Johnson → DOB verification)*:
    > "Thank you, Michael. For security purposes, could you please verify your date of birth?"

12. **Caller:**
    > "July 22nd, 1990."

13. **Agent** *(DOB matches 1990-07-22, reads claim status: pending)*:
    > "Thank you, I've verified your identity. Your claim CLM-2024-002 is currently under review. Our team is working on it and you should receive an update soon. Is there anything else I can help with?"

14. **Caller:**
    > "No, thanks."

15. **Agent** *(calls `log_interaction`, sentiment="neutral")*:
    > "For your records, your claim number is CLM-2024-002. Thank you for calling Observe Insurance. Have a wonderful day!"

16. **Agent** *(calls `endCall`)*

### Verification Points

- [ ] Re-verification triggered after identity denial
- [ ] Multi-match handled: asks for first name to disambiguate
- [ ] DOB verification requested and confirmed before revealing claim info
- [ ] Correct claim status (pending) delivered
- [ ] Interaction logged in Airtable

---

## Scenario B: Phone Not Found + Abrupt Hangup

**Caller profile:** Unknown caller, phone not in Airtable
**Setup:** Caller gives a number that doesn't exist in Customers table, then hangs up mid-conversation.

---

### Call Flow

1. **Agent (auto-greeting):**
   > "Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?"

2. **Caller:**
   > "Yeah I need to check my claim."

3. **Agent:**
   > "Sure, could you give me the phone number on your account?"

4. **Caller:**
   > "555-000-9999."

5. **Agent** *(calls `lookup_caller` with phone_number → not found)*:
   > "I wasn't able to find an account associated with that phone number. Let me arrange for a representative to follow up with you. You should receive a callback within 24 hours."

6. **Caller** *(hangs up abruptly — VAPI detects silence/disconnect)*

7. *(VAPI sends end-of-call-report to n8n)*

### Verification Points

- [ ] "Not found" response delivered correctly (no crash, no confusion)
- [ ] Agent offers callback arrangement gracefully
- [ ] End-of-call-report fires even on abrupt hangup
- [ ] Interaction row created via end-of-call-report (fallback logging since `log_interaction` was never called)
- [ ] caller_name logged as "Unknown" in the interaction

---

## Scenario C: Requires Documentation Flow

**Caller profile:** Emily Chen, phone +12125559876, claim CLM-2024-003 (requires_documentation)

---

### Call Flow

1. **Agent (auto-greeting):**
   > "Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?"

2. **Caller:**
   > "I'm calling about my claim."

3. **Agent:**
   > "Of course. What's the phone number on your account?"

4. **Caller:**
   > "212-555-9876."

5. **Agent** *(calls `lookup_caller` → matches Emily Chen)*:
   > "Am I speaking with Emily Chen?"

6. **Caller:**
   > "Yes."

7. **Agent** *(DOB verification)*:
   > "For security purposes, could you please verify your date of birth?"

8. **Caller:**
   > "November 4th, 1978."

9. **Agent** *(DOB matches 1978-11-04, reads claim status: requires_documentation)*:
   > "Your claim requires some additional documentation before we can proceed. You can upload the documents through our online portal, or email them directly to support@observeinsurance.com. Would you like me to go over what's needed?"

10. **Caller:**
    > "Yes please."

11. **Agent** *(reads claim_details)*:
    > "We need a proof of loss form and photos of the damage. You can send those to support@observeinsurance.com. Is there anything else I can help with?"

12. **Caller:**
    > "No, that's it. Thank you."

13. **Agent** *(calls `log_interaction`, sentiment="neutral")*:
    > "For your records, your claim number is CLM-2024-003. Thank you for calling Observe Insurance. Have a wonderful day!"

14. **Agent** *(calls `endCall`)*

### Verification Points

- [ ] DOB verification requested and confirmed before revealing claim info
- [ ] "Requires documentation" status communicated with next steps
- [ ] claim_details read aloud when caller requests specifics
- [ ] Interaction logged correctly
