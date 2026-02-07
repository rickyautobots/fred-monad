# FRED-Monad Demo Script (2 minutes)

**Purpose:** Demo video for Moltiverse hackathon submission
**Length:** ~2 minutes
**Tool:** QuickTime or Loom screen recording

---

## Pre-Recording Setup

```bash
cd ~/.openclaw/workspace/projects/fred-monad
# Make sure terminal is visible, font size readable
```

---

## Script

### Intro (10 sec)
**Show:** README.md in editor or browser

**Say:** "This is FRED — an autonomous Polymarket trading agent, now adapted for Monad's high-throughput blockchain."

### Architecture Overview (20 sec)
**Show:** Scroll through `fred_monad.py` briefly

**Say:** "FRED uses optimal-f position sizing and makes trading decisions based on market probability analysis. The core engine handles market scanning, probability estimation, and autonomous trade execution."

### Demo Run (60 sec)
**Run:**
```bash
./demo.sh
```

**Say:** "Here's FRED in action on Monad testnet. It's scanning markets, calculating expected value, and generating trade signals. The system tracks all positions and manages risk automatically."

*Let demo run, show output scrolling*

### Key Features (20 sec)
**Show:** Terminal output

**Say:** 
- "Real-time market scanning via Monad RPC"
- "LLM-powered probability estimation"
- "Optimal position sizing with Kelly criterion"
- "Full position tracking and P&L monitoring"

### Close (10 sec)
**Show:** GitHub URL

**Say:** "FRED is open source on GitHub. Built for the Moltiverse hackathon — agents that transact at scale on Monad."

---

## Post-Recording

1. Trim any dead time
2. Upload to YouTube (unlisted) or Loom
3. Submit at: https://forms.moltiverse.dev/submit

---

## Submit Form Fields Needed

- **Project Name:** FRED
- **GitHub:** https://github.com/rickyautobots/fred-monad
- **Demo Video:** [YouTube/Loom URL]
- **Track:** Agent Track (no token)
- **Category:** Trading Agents / DeFi

---

*Prepared by Ricky for Derek to record*
