// VAPI Custom Knowledge Base endpoint.
// Receives knowledge-base-request from VAPI, embeds the query with gte-small,
// searches pgvector via match_faqs RPC, returns documents in VAPI's expected format.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const model = new Supabase.ai.Session("gte-small");

Deno.serve(async (req) => {
  try {
    const bodyBytes = new Uint8Array(await req.arrayBuffer());
    const bodyText = new TextDecoder().decode(bodyBytes);

    // Verify VAPI webhook secret via x-vapi-signature (HMAC SHA256)
    const signature = req.headers.get("x-vapi-signature");
    const secret = Deno.env.get("VAPI_SECRET");
    if (signature && secret) {
      const key = await crypto.subtle.importKey(
        "raw",
        new TextEncoder().encode(secret),
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["sign"]
      );
      const sig = await crypto.subtle.sign("HMAC", key, bodyBytes);
      const expected = `sha256=${Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, "0")).join("")}`;
      if (signature !== expected) {
        return new Response("Unauthorized", { status: 401 });
      }
    }

    const { message } = JSON.parse(bodyText);

    // Only handle knowledge-base-request messages
    if (message.type !== "knowledge-base-request") {
      return Response.json({ documents: [] });
    }

    // Extract latest user message
    const userMessages = message.messages.filter(
      (m: { role: string }) => m.role === "user"
    );
    const query = userMessages[userMessages.length - 1]?.content || "";

    if (!query) {
      return Response.json({ documents: [] });
    }

    // Generate embedding for query
    const embedding = await model.run(query, {
      mean_pool: true,
      normalize: true,
    });

    // Similarity search via RPC
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
    );

    const { data, error } = await supabase
      .rpc("match_faqs", {
        query_embedding: embedding,
        match_threshold: 0.8,
      })
      .select("id, question, answer, category")
      .limit(3);

    if (error) {
      console.error("match_faqs error:", error);
      return Response.json({ documents: [] });
    }

    // Return in VAPI Custom Knowledge Base format
    return Response.json({
      documents: (data || []).map(
        (faq: {
          id: number;
          question: string;
          answer: string;
          category: string;
        }) => ({
          content: `Q: ${faq.question}\nA: ${faq.answer}`,
          similarity: 1.0,
          uuid: `faq-${faq.id}`,
        })
      ),
    });
  } catch (err) {
    console.error("search-faq error:", err);
    return Response.json({ documents: [] });
  }
});
