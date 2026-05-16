# JCESOM Student Journey Decision Lab

A Streamlit leadership policy refresher for the **Marshall University Joan C. Edwards School of Medicine**, built in Marshall's kelly green and black brand palette. Nine real-world student scenarios. At each step the user chooses who is responsible — and learns why, grounded in the SOM Student Handbook.

Built by SinglePoint Analytics, LLC.

---

## What's in it

**Nine scenarios, 55 decision points:**

| # | Student | Level | Theme |
|---|---|---|---|
| 1 | Sarah B. | Levels 1–4 | Project PreMed → legacy → restart → lapse → clean finish |
| 2 | Marcus T. | MD/PhD | Phase 1 → research years → Phase 2/3 re-entry |
| 3 | Aaliyah J. | Level 1 | Food insecurity (open disclosure pathway) |
| 4 | Jamal R. | Level 3 | New parent, no childcare, considering part-time work |
| 5 | David O. | Level 2 | Sole breadwinner; first exam failure & remediation |
| 6 | Sasha K. | Level 2 | Honor Code — AI on assessment |
| 7 | **Devon P.** | Level 3 | **Hidden food insecurity — hunger eroding study & rounds** |
| 8 | Maya R. | Levels 1→2 | Pregnancy, delivery, postpartum depression |
| 9 | Tyler M. | Level 3 | Substance use disorder on clerkship |

Each step sets a situation, asks who is responsible, presents four plausible offices, then reveals the correct office, why it's right, why the others are wrong, and the governing policy.

The sidebar tracks scenario progress and overall score. Each scenario ends with a debrief and decision-by-decision review.

---

## Branding

The app uses Marshall University's brand palette:
- **Marshall Kelly Green** `#00B140` (primary)
- **Deep Green** `#007934` (banner background)
- **Black** `#000000` (sidebar + accents, echoing the Phase 3 banner)
- **White** for surfaces

Typography pairs **Cormorant Garamond** (institutional wordmark, serif) with **Fraunces** (italic display) and **Inter** (body).

### Swapping in the official Marshall M logo

The banner currently renders a placeholder "M" mark in brand colors. To use the official JCESOM logo:

1. Drop the official PNG or SVG file in the project root (e.g. `marshall_m.png`).
2. In `app.py`, find the banner block (search for `class="logo-mark"`) and replace the inner `<span class="m-letter">M</span>` with an `<img>` tag. The simplest approach:

   ```python
   import base64
   with open("marshall_m.png", "rb") as f:
       logo_b64 = base64.b64encode(f.read()).decode()
   # then in the banner markdown f-string, replace <span class="m-letter">M</span> with:
   # <img src="data:image/png;base64,{logo_b64}" style="width:60px;height:60px;" />
   ```

3. Or host the logo at a public URL and use `<img src="https://..." />` directly.

Marshall's official brand assets and usage guidelines are available through Marshall University Communications.

---

## Run locally

Python 3.9+:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Deploy to Streamlit Community Cloud (free)

1. Create a new GitHub repo and push `app.py`, `requirements.txt`, and `README.md`.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, point it at your repo, choose `app.py` as the main file, deploy.

Live in ~2 minutes at a `*.streamlit.app` URL. Auto-redeploys on every push.

---

## Deploy elsewhere

Single Python file, one dependency. Runs anywhere Streamlit runs:
- **Render / Railway / Fly.io** — start command `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- **HuggingFace Spaces** — Streamlit SDK template
- **Internal server** — `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`

---

## Editing scenarios

All scenario data lives in `SCENARIOS` near the top of `app.py`. Each scenario dict has `id`, `name`, `level`, `tagline`, `background`, and a `steps` list. Each step:

```python
{
    "situation": "...",
    "question": "...",
    "options": {"OSA": "...", "APSC": "..."},
    "correct": "OSA",
    "why_right": "...",
    "why_wrong": {"APSC": "...", "...": "..."},
    "policy": "...",
}
```

Add a stakeholder by adding to the `STAKEHOLDERS` dict at the top.

---

## Source

Marshall University Joan C. Edwards School of Medicine — Student Handbook (July 2024):
https://jcesom.marshall.edu/media/63252/som_studenthandbook_july2024.pdf
