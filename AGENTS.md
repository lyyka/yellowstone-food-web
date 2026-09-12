## Learned User Preferences

- Keep the app educational and playful to explore, not a dry scientific graph tool.
- Prefer a species-first catalog with a richer per-species graph over one global food-web diagram.
- Treat natural-language prompting as the primary experience on its own centered page (Cursor/Lovable-style), with chat history visually separate from main navigation.
- Grok/xAI answers should sound natural, human, and imaginative rather than terse ecological summaries.
- Color, underline, and make species mentions in Grok answers hoverable, with a short-info popup and image.
- Position the chat for tourists: invite wild what-if questions and finish with a souvenir postcard they could buy later.
- Keep Fal AI postcard prompts tightly faithful to the visitor's premise so generated images match the asked scenario.
- Make social/link-preview title, description, and image catchy and fun, featuring nature and animals.
- Species admin should support standard CRUD plus CSV bulk import with a downloadable example file.
- Supply xAI credentials through `.env` (`XAI_API_KEY`); Fal (`FAL_KEY`) is an optional postcard fallback. Do not commit secrets.

## Learned Workspace Facts

- Yellowstone-scoped food-web playground: iNaturalist research-grade mammals, GloBI who-eats-whom among those taxa, plus a few seeded park links when GloBI is sparse.
- Cascades are qualitative graph walks, not population models.
- Stack is FastAPI (`api/`, uvicorn on port 8000) and Vite/React (`web/`, port 5173).
- Graph snapshot lives at `data/graphs/yellowstone-mammals.json`; refresh with `scripts/ingest_globi.py`.
- xAI Grok (`XAI_API_KEY`, default `XAI_MODEL=grok-4`) interprets and narrates scenarios.
- xAI Grok Imagine (`XAI_IMAGE_MODEL`, default `grok-imagine-image-2.0`) generates souvenir postcard stills; Fal Flux is the fallback if xAI returns nothing.
- Imaginative visitor prompts are first-class imagine/postcard scenarios, not forced species-removal plans.
- Main surfaces are Ask (prompt + history + postcard), species catalog/dossier, and Manage (CRUD/CSV).
- Open Graph / Twitter previews use `VITE_PUBLIC_ORIGIN` as the absolute site origin.
