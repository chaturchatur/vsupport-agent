# Happy Path Demo Script

## Scenario: Authenticated caller checks approved claim status

**Caller profile:** Sarah Johnson, phone +14155551234, claim CLM-2024-001 (approved)

---

### Call Flow

1. **Agent (auto-greeting):**
   > "Thank you for calling Observe Insurance. My name is Sarah. How can I help you today?"

2. **Caller:**
   > "Hi, I'm calling to check on the status of my claim."

3. **Agent:**
   > "Of course, I'd be happy to help. Could you please provide the phone number associated with your account?"

4. **Caller:**
   > "Sure, it's 415-555-1234."

5. **Agent** *(calls `lookup_caller` with phone_number → single match)*:
   > "Am I speaking with Sarah Johnson?"

6. **Caller:**
   > "Yes, that's me."

7. **Agent** *(DOB verification)*:
   > "For security purposes, could you please verify your date of birth?"

8. **Caller:**
   > "March 15th, 1985."

9. **Agent** *(DOB matches 1985-03-15)*:
   > "Thank you, I've verified your identity. Great news — your claim CLM-2024-001 has been approved! Is there anything else you'd like to know about your claim?"

10. **Caller:**
    > "No, that's all I needed. Thank you!"

11. **Agent** *(calls `log_interaction` with caller_name="Sarah Johnson", sentiment="positive")*:
    > "For your records, your claim number is CLM-2024-001. Thank you for calling Observe Insurance. Have a wonderful day!"

12. **Agent** *(calls `endCall`)*

---

### Expected Airtable State After Call

**Interactions table** — new row:
| Field | Value |
|-------|-------|
| caller_name | Sarah Johnson |
| phone_number | +14155551234 |
| summary | Caller checked claim status. Claim CLM-2024-001 approved. |
| sentiment | positive |
| vapi_call_id | *(auto from end-of-call-report)* |

### Verification Points

- [ ] Agent greets, asks for phone, identifies caller by name
- [ ] DOB verification requested and confirmed before revealing claim info
- [ ] Claim status "approved" communicated correctly
- [ ] `log_interaction` tool called before goodbye
- [ ] `endCall` triggered after caller confirms no more questions
- [ ] Interaction row created in Airtable
- [ ] End-of-call-report dedup: only one Interactions row (not two)
