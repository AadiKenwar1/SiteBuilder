import { NextResponse } from "next/server"
import { uploadLeadPhotos, IMG_EXT, MAX_FILE_BYTES } from "@/lib/crm.server"

type Ctx = { params: Promise<{ slug: string }> }

// POST /api/leads/:slug/photos — multipart FormData, field name "images" (repeatable).
// Validates ext + size, uploads to lead-photos/<slug>/, updates photo_urls.
export async function POST(req: Request, { params }: Ctx) {
  const { slug } = await params
  try {
    const form = await req.formData()
    const raw = form.getAll("images")
    const files: { bytes: Uint8Array; name: string }[] = []

    for (const entry of raw) {
      if (!(entry instanceof File)) continue
      const ext = "." + (entry.name.split(".").pop() ?? "").toLowerCase()
      if (!IMG_EXT.has(ext))
        return NextResponse.json({ error: `Unsupported type: ${entry.name}` }, { status: 400 })
      if (entry.size > MAX_FILE_BYTES)
        return NextResponse.json({ error: `File too large (max 5 MB): ${entry.name}` }, { status: 400 })
      files.push({ bytes: new Uint8Array(await entry.arrayBuffer()), name: entry.name })
    }

    if (files.length === 0)
      return NextResponse.json({ error: "No valid image files provided" }, { status: 400 })

    const photoUrls = await uploadLeadPhotos(slug, files)
    return NextResponse.json({ ok: true, photo_urls: photoUrls })
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 })
  }
}
