# Issue Positions Visualization Tool

## Project Overview

A public-facing educational tool that visualizes where members of Congress stand on specific policy issues, revealing:
- **Intra-party diversity**: The range of positions within each party
- **Cross-party overlap**: Where Democrats and Republicans actually agree
- **Evidence-based positioning**: Derived from voting records AND public statements

### Core Insight
Media coverage flattens political positions into "two teams." This tool shows the real complexity—that on many issues, there's more diversity within parties and more agreement across parties than people realize.

---

## MVP Scope

**Phase 1 Target:** One issue (Trade Policy), Senate only (100 members)

Why Trade Policy?
- Known for scrambling traditional left-right alignment
- Populist vs. establishment splits in both parties
- Recent high-profile votes (tariffs, trade agreements) provide clear data
- Interesting cross-party coalitions

Why Senate first?
- 100 members vs 435 (manageable)
- Senators have more documented positions
- Longer terms = more voting history per member

---

## Data Sources

### Primary Sources

| Source | Data Type | Access Method | Notes |
|--------|-----------|---------------|-------|
| ProPublica Congress API | Votes, bills, member info | REST API (free) | Good for recent Congresses |
| Congress.gov | Bill text, voting records | Bulk data / API | Official source |
| Congressional Record | Floor speeches | GPO bulk data | Text of all floor proceedings |
| VoteSmart | Interest group ratings, positions | API (free tier) | Political Courage Test responses |
| GovTrack | Votes, ideology scores | API + bulk data | Good historical coverage |

### Secondary Sources (for enrichment)
- Official press releases (.gov sites)
- Committee hearing transcripts
- Verified social media (with caution)

### Data NOT to use initially
- News articles (interpretation layer)
- Campaign websites (often outdated)
- Unverified social media

---

## Tech Stack

### Frontend
- **React** - Component architecture
- **D3.js** - Custom visualizations
- **Tailwind CSS** - Styling

### Backend
- **Python FastAPI** - API server
- **SQLite** (MVP) → **PostgreSQL** (production)
- **Claude API** - Statement analysis and position extraction

### Infrastructure (later)
- Vercel or Netlify (frontend hosting)
- Railway or Render (backend hosting)

---

## Data Model

### Core Entities

```
members
├── id (bioguide_id)
├── name
├── state
├── party
├── chamber (senate/house)
├── current_term_start
└── photo_url

issues
├── id
├── name (e.g., "Trade Policy")
├── description
├── slug
└── sub_positions[] (defined spectrum endpoints)

positions
├── id
├── member_id (FK)
├── issue_id (FK)
├── score (float, -1.0 to 1.0)
├── confidence (float, 0 to 1.0)
├── last_updated
└── summary (AI-generated position description)

evidence
├── id
├── position_id (FK)
├── type (vote | statement | rating)
├── source_url
├── source_date
├── raw_text (for statements)
├── extracted_position (AI analysis)
└── weight (how much this evidence contributes)

votes
├── id
├── bill_id
├── member_id (FK)
├── vote (yes | no | abstain | not_voting)
├── date
└── issue_tags[] (which issues this vote relates to)
```

### Position Scoring Approach

Each member's position on an issue is a **weighted composite**:
- Relevant votes (highest weight - these are actions)
- Public statements (medium weight - these are words)
- Interest group ratings (lower weight - external interpretation)

Score range: **-1.0 to +1.0**
- For Trade Policy: -1.0 = Strong free trade, +1.0 = Strong protectionist
- Neutral/mixed positions cluster near 0

Confidence score reflects:
- Volume of evidence
- Consistency of evidence
- Recency of evidence

---

## Issue Taxonomy (20 Issues for Full Build)

### Economic & Trade
1. **Trade policy and tariffs** ← MVP ISSUE
2. Antitrust and big tech regulation
3. Minimum wage
4. Labor rights and union policy
5. Social Security and Medicare reform

### Foreign Policy & Defense
6. Military spending levels
7. Foreign military intervention
8. Aid to Ukraine
9. Israel-Palestine policy
10. China policy

### Social & Cultural
11. Abortion access
12. Gun policy
13. LGBTQ+ rights
14. Marijuana legalization
15. Criminal justice reform

### Environment & Energy
16. Climate change response
17. Energy production mix

### Governance & Rights
18. Immigration policy
19. Voting rights and election administration
20. Government surveillance and privacy

### Sub-position Spectrum (Trade Policy Example)

```
TRADE POLICY SPECTRUM

-1.0                    0                     +1.0
|---------------------|---------------------|
Free Trade            Mixed/Nuanced         Protectionist

Key indicators:
- Support for tariffs (+ = protectionist)
- Support for trade agreements like TPP, USMCA (- = free trade)
- "Buy American" provisions (+ = protectionist)
- Opposition to outsourcing (+ = protectionist)
```

---

## Methodology (Transparency Document)

### How Positions Are Determined

#### Step 1: Vote Collection
- Identify bills tagged to the issue (trade policy)
- Pull member votes on those bills
- Weight recent votes higher than older votes

#### Step 2: Statement Collection
- Scrape Congressional Record floor speeches
- Collect official press releases
- Filter to statements mentioning issue keywords

#### Step 3: AI Analysis (Claude)
- For each statement, extract:
  - Position expressed (-1 to +1)
  - Confidence in interpretation
  - Key quotes
- Prompt designed for consistency and neutrality

#### Step 4: Score Aggregation
```
final_score = (
    0.5 * weighted_vote_score +
    0.35 * weighted_statement_score +
    0.15 * interest_group_score
)
```

#### Step 5: Human Review (for edge cases)
- Flag members with high-variance evidence
- Flag members with very low evidence volume

### What We DON'T Do
- Make value judgments (neither end of spectrum is "better")
- Predict future votes
- Rate members as "good" or "bad"

---

## Phased Build Plan

### Phase 1: MVP (Weeks 1-2)
**Goal:** Trade policy positions for all 100 senators, working end-to-end

- [ ] Set up project structure
- [ ] Create member database (Senate only)
- [ ] Build vote collection pipeline (trade-related bills)
- [ ] Build statement collection pipeline (Congressional Record)
- [ ] Develop Claude prompts for position extraction
- [ ] Create position scoring algorithm
- [ ] Build basic spectrum visualization (D3)
- [ ] Add member detail view with evidence

**Deliverable:** Working prototype with real data

### Phase 2: Expand Issues (Weeks 3-4)
- [ ] Add 4 more issues (total of 5)
- [ ] Refine AI prompts based on Phase 1 learnings
- [ ] Add issue comparison view (2-axis scatterplot)
- [ ] Improve UI/UX

### Phase 3: Expand to House (Weeks 5-6)
- [ ] Add all 435 House members
- [ ] Optimize data pipeline for scale
- [ ] Add filtering (by state, by party, by chamber)

### Phase 4: Polish for Public (Weeks 7-8)
- [ ] Add all 20 issues
- [ ] Design pass (visual polish)
- [ ] Add "Find Your Rep" entry point
- [ ] Add methodology documentation for users
- [ ] Performance optimization
- [ ] Deploy to production

### Phase 5: Enhancements (Ongoing)
- [ ] Statement search (let users explore raw evidence)
- [ ] Historical view (how positions changed over time)
- [ ] Export/embed functionality
- [ ] Mobile optimization

---

## Success Metrics

### Technical
- Data freshness < 1 week
- Position coverage > 95% of members
- Page load < 2 seconds

### User Experience
- Users can understand a member's position in < 30 seconds
- Evidence is always one click away
- Methodology is transparent and findable

### Impact
- Users discover unexpected overlaps
- Users learn something they didn't know
- Media/educators reference the tool

---

## File Structure

```
issue-positions/
├── PROJECT_PLAN.md              # This file
├── README.md                    # Public-facing project description
├── docs/
│   ├── METHODOLOGY.md           # Detailed scoring methodology
│   ├── DATA_SOURCES.md          # API documentation and access
│   └── ISSUE_TAXONOMY.md        # Full issue definitions
├── data/
│   ├── raw/                     # Raw collected data
│   ├── processed/               # Cleaned and structured data
│   └── seed/                    # Initial seed data (member lists)
├── scripts/
│   ├── collect_votes.py         # Vote collection pipeline
│   ├── collect_statements.py    # Statement collection pipeline
│   ├── analyze_positions.py     # Claude API integration
│   ├── calculate_scores.py      # Position scoring
│   └── utils/
├── api/
│   ├── main.py                  # FastAPI application
│   ├── routes/
│   ├── models/
│   └── services/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SpectrumChart.jsx
│   │   │   ├── MemberCard.jsx
│   │   │   ├── EvidencePanel.jsx
│   │   │   └── IssueSelector.jsx
│   │   ├── pages/
│   │   └── utils/
│   └── public/
├── tests/
└── .env.example                 # Environment variables template
```

---

## Getting Started (First Claude Code Session)

1. Initialize the project:
```bash
mkdir issue-positions
cd issue-positions
git init
npm init -y  # or set up Python environment
```

2. Start Claude Code:
```bash
claude
```

3. First prompt:
> "Read PROJECT_PLAN.md. Let's start Phase 1 by setting up the project structure and creating the database schema for members, issues, positions, and evidence. Use SQLite for the MVP."

---

## Open Questions (To Resolve During Build)

1. **Statement collection scope:** How far back should we go? 1 Congress? 2?
2. **Vote selection:** Who decides which votes are "about" trade policy?
3. **Confidence thresholds:** Below what confidence do we show "insufficient data"?
4. **Update frequency:** Daily? Weekly? On-demand?
5. **Handling contradictions:** What if votes and statements conflict?

---

## Resources

- [ProPublica Congress API Docs](https://projects.propublica.org/api-docs/congress-api/)
- [Congress.gov API](https://api.congress.gov/)
- [GovTrack Bulk Data](https://www.govtrack.us/developers)
- [VoteSmart API](https://votesmart.org/share/api)
- [Voteview Data](https://voteview.com/data)
- [Congressional Record via GPO](https://www.govinfo.gov/bulkdata/CREC)

---

*Last updated: January 2026*
*Status: Planning*
