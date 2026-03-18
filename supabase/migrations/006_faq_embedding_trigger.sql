-- Auto-trigger embedding generation when FAQ rows are inserted or updated.
-- Uses pg_net to call the generate-embedding Edge Function via HTTP.

-- Enable pg_net extension (provides net.http_post for async HTTP calls)
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- Function that calls the generate-embedding Edge Function
CREATE OR REPLACE FUNCTION generate_faq_embedding()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Call the generate-embedding Edge Function with the new/updated record
  PERFORM extensions.http_post(
    url := current_setting('app.settings.supabase_url') || '/functions/v1/generate-embedding',
    body := jsonb_build_object('record', jsonb_build_object(
      'id', NEW.id,
      'question', NEW.question,
      'answer', NEW.answer
    )),
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key')
    )
  );

  RETURN NEW;
END;
$$;

-- Trigger on INSERT or UPDATE (only when question/answer change)
CREATE TRIGGER faq_embedding_trigger
  AFTER INSERT OR UPDATE OF question, answer
  ON faqs
  FOR EACH ROW
  EXECUTE FUNCTION generate_faq_embedding();
