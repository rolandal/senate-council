---
pack: figures-index
mode: figures
default_panel: [socrates, feynman, munger, taleb, torvalds]
bench: [ada, aristotle, aurelius, feynman, kahneman, karpathy, lao-tzu, machiavelli, meadows, munger, musashi, rams, socrates, sun-tzu, sutskever, taleb, torvalds, watts, jacobs, hopper, naval, graham, musk]
description: >
  Index for Mode 2 (Figures). The default panel is 5 lens-orthogonal minds. Use a triad for
  zero-config topical runs, or build a custom panel by sub (`swap X→Y`) and add (`+name`,
  grow up to ~8). Polarity pairs (each figure's natural opposite) are read from each figure's
  own frontmatter; the map below is a quick reference.
---

# Figures — Bench Index, Triads & Polarity Map

## Default panel (5)

**Socrates · Feynman · Munger · Taleb · Torvalds** — assumption-destroyer /
first-principles rebuilder / inverter / tail-risk / pragmatic shipper. Chosen for
maximal lens-orthogonality; maps cleanly onto the thinking-style skeleton so the
chairman synthesis transfers unchanged.

## The full bench (23)

| Slug | Figure | Lens |
|------|--------|------|
| socrates | Socrates | assumption destruction |
| feynman | Richard Feynman | first-principles / rebuild-from-scratch |
| munger | Charlie Munger | inversion + mental models + incentives |
| taleb | Nassim Taleb | antifragility / tail risk |
| torvalds | Linus Torvalds | pragmatic engineering / taste |
| aristotle | Aristotle | classification / empiricism / golden mean |
| aurelius | Marcus Aurelius | stoicism / control vs not / duty |
| kahneman | Daniel Kahneman | cognitive bias / base rates |
| karpathy | Andrej Karpathy | AI/ML pragmatism / "some things are genuinely new" |
| sutskever | Ilya Sutskever | deep learning / scaling / AI safety |
| meadows | Donella Meadows | systems thinking / leverage points |
| rams | Dieter Rams | less-but-better / honest design |
| jacobs | Jane Jacobs | ground-truth urbanism / bottom-up emergence |
| hopper | Grace Hopper | pragmatic execution / institutional courage |
| naval | Naval Ravikant | leverage / long-term games / clarity |
| graham | Paul Graham | startup first-principles / makers |
| musk | Elon Musk | physics-first / velocity / extreme ambition |
| machiavelli | Niccolò Machiavelli | power / realpolitik / ends-means |
| sun-tzu | Sun Tzu | strategy / terrain / win-before-fighting |
| musashi | Miyamoto Musashi | single-combat strategy / discipline |
| lao-tzu | Lao Tzu | wu wei / natural order |
| watts | Alan Watts | perspective / the illusion of separateness |
| ada | Ada Lovelace | formal rigor / the first programmer |

## Zero-config triads

| Triad | Members | Use for |
|-------|---------|---------|
| `decision` | munger · kahneman · aristotle | general decision quality, bias, structure |
| `economics` | munger · taleb · naval | money, incentives, risk, leverage |
| `ai-strategy` | karpathy · sutskever · taleb | AI/ML product & research bets |
| `startup` | graham · naval · musk | 0→1, growth, founder calls |
| `strategy` | sun-tzu · musashi · machiavelli | competitive / adversarial moves |
| `design` | rams · jacobs · torvalds | product/UX, simplicity, ground-truth |
| `first-principles` | feynman · musk · socrates | rebuild the problem from scratch |
| `wisdom` | aurelius · lao-tzu · watts | life, meaning, equanimity, perspective |
| `systems` | meadows · munger · kahneman | second-order effects, feedback loops |
| `execution` | hopper · torvalds · musk | ship-it, velocity, cut-the-theory |

## Polarity map (quick reference)

Each figure's `polarity_pairs` frontmatter names its natural intellectual opposite,
used to auto-balance a panel. Examples: munger↔aristotle (cross-model breadth vs
single-system depth), musk↔taleb (raise-the-bar risk vs fragility caution),
jacobs↔top-down power, hopper↔restraint/process, naval↔short-term tactics,
graham↔systems/scale. The authoritative pairs live in each figure file.
