# Product

<!-- impeccable:product-schema 1 -->

All facts below come from TASK.md (the user's written brief). No interview was held; the brief allows one question round, used for hardware, Kaggle key and study availability. Items marked (inferred) are inferences from that brief.

## Platform

web

## Stack

Pinned by brief: FastAPI, one static/index.html, one app.css, one app.js. No build step, no framework. SQLite (app.db). Runs locally at localhost:7860 via `python -m app`.

## Users

A design student / textile designer (inferred: the author and their evaluators) composing Warli-inspired repeat patterns for print, and examiners reviewing how each generative AI stage works. A morning annotator and survey respondent use the hidden /study route.

## Product Purpose

Chhaap generates seamless, print-ready Warli motif repeats on a local machine with open models, and pairs each output with a meaning card whose symbols are known because the system placed them. Success: story -> generate -> repeat view -> meaning card -> export works end to end, and every stage is visible.

## Positioning

Compose-then-stylize: symbols are placed on a toroidal canvas from a sourced lexicon before diffusion, so the meaning card is true by construction, and circular padding makes the tile repeat without a visible join.

## Operating Context

Runs on a CPU-only laptop (Intel Core Ultra 7, 15 GB RAM); a generation takes tens of seconds, so progress and step previews matter. Used at a 1280px laptop width and at phone width.

## Capabilities and Constraints

- Free, open models only; no paid APIs. No e-commerce (no cart, payments, store); product mockups are allowed.
- Every export carries "AI-generated, Warli-inspired. Not a GI-certified Warli painting."
- Meaning card ends with "Meanings not yet verified by a Warli artist."
- Training data license: unclear, scraped; research use only. Must be stated in the app.

## Brand Commitments

Name: Chhaap (Hindi/Marathi for "print/stamp"; inferred gloss). Brief-pinned look: a block-printer's workbench, not a SaaS dashboard; geru/ochre ground, rice-paste off-white, charcoal ink, one accent at most; one characterful display face and one clean text face from Google Fonts; monospace only in the "under the hood" panel; no purple gradients, glassmorphism or emoji.

## Evidence on Hand

data/lexicon.csv (25 sourced symbols), generated runs in runs/, eval results in eval/results/. No testimonials, customers or artisan endorsements exist; none may be implied.

## Product Principles

- Show the machine: every stage of generation is inspectable.
- Never claim what the system did not do: meanings come from the lexicon, numbers from result files.
- Credit the tradition: provenance, GI status and labels are part of the product, not a footer.

## Accessibility & Inclusion

Keyboard-operable controls, visible focus, sufficient contrast on the ochre ground (inferred standard: WCAG AA).
