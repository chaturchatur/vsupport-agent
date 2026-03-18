// Auto-generate embeddings when FAQ rows are inserted or updated.
// Triggered via Supabase Database Webhook on the `faqs` table (INSERT + UPDATE events).

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const model = new Supabase.ai.Session("gte-small");

Deno.serve(async (req) => {
  try {
    const { record } = await req.json();

    if (!record?.id || !record?.question || !record?.answer) {
      return new Response("Missing required fields", { status: 400 });
    }

    // Generate embedding from question + answer combined
    const input = `${record.question} ${record.answer}`;
    const embedding = await model.run(input, {
      mean_pool: true,
      normalize: true,
    });

    // Update the row with the generated embedding
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { error } = await supabase
      .from("faqs")
      .update({ embedding })
      .eq("id", record.id);

    if (error) {
      console.error("Failed to update embedding:", error);
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ success: true, id: record.id }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error("generate-embedding error:", err);
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});
