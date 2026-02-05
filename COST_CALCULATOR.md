# PantryBot Cost Calculator

## Current Pricing (Claude Haiku 4.5)

| Component | Price |
|-----------|-------|
| Input tokens | $0.25 per million |
| Output tokens | $1.25 per million |

## Typical Interaction Breakdown

### Recipe Search + View + Save (Full Flow)

**Input Tokens:**
- System prompt: ~100 tokens
- Tool definitions: ~2,000 tokens
- Conversation history: ~500 tokens (last 10 messages)
- User message: ~50 tokens
- Tool results: ~1,500 tokens
- **Total input per call:** ~4,150 tokens

**Output Tokens:**
- Recipe presentation: ~200 tokens
- Full recipe details: ~300 tokens
- **Total output:** ~500 tokens

**Iterations:**
- Search recipes: 2 API calls
- Get full recipe: 2 API calls
- Save to Grocy: 2 API calls
- **Total:** ~6 API calls per complete interaction

### Cost Per Interaction

```
Input:  6 calls × 4,150 tokens = 24,900 tokens = $0.006
Output: 6 calls × 500 tokens   =  3,000 tokens = $0.004
───────────────────────────────────────────────────────
Total: ~$0.01 per complete recipe interaction
```

## Real-World Usage

### Monthly Scenarios

| Usage Level | Interactions/Month | Monthly Cost | Annual Cost |
|-------------|-------------------|--------------|-------------|
| Light (2/week) | 8 | $0.08 | $0.96 |
| Moderate (4/week) | 16 | $0.16 | $1.92 |
| Heavy (daily) | 30 | $0.30 | $3.60 |
| Family (10/week) | 40 | $0.40 | $4.80 |

### API Credit Lifespan

| Credit Amount | Interactions | Duration (10/week) |
|---------------|--------------|-------------------|
| $5 | ~500 | ~12 months |
| $10 | ~1,000 | ~24 months |
| $20 | ~2,000 | ~48 months |

## Comparison: PantryBot vs Subscriptions

| Service | Cost | What You Get |
|---------|------|--------------|
| **PantryBot** | $5/year | Unlimited recipes, pantry tracking, meal planning |
| Paprika | $29.99/year | Recipe manager only |
| Mealime | $49.99/year | Meal planning |
| AnyList | $11.99/year | Shopping lists + recipes |
| Yummly | $59.99/year | Recipe discovery |

**Savings vs average subscription: ~$40-55/year**

## Spoonacular API (Recipe Search)

| Tier | Cost | Requests/Day | Requests/Month |
|------|------|--------------|----------------|
| Free | $0 | 150 | 4,500 |
| Basic | $19/month | 1,500 | 45,000 |

**Typical PantryBot usage:**
- 2-5 Spoonacular requests per recipe search
- ~10 searches/week = 40/month = ~160 API calls
- **Free tier easily covers most families**

## Total Cost of Ownership (Annual)

### Conservative Estimate
```
Claude API:          $5/year
Spoonacular:         $0/year (free tier)
Docker/Hosting:      $0/year (self-hosted)
──────────────────────────────
Total:               $5/year
```

### If You Exceed Free Tiers
```
Claude API:          $10/year
Spoonacular Basic:   $228/year (if >150 req/day)
──────────────────────────────
Total:               $238/year
(Still less than Yummly alone!)
```

## Current Optimizations ✅

These are already applied:

1. **Using Haiku** instead of Sonnet (12x cheaper)
2. **Trimmed system prompt** (78% token reduction)
3. **Limited conversation history** (last 10 messages only)
4. **Reduced max output** (2048 vs 4096 tokens)

**Result:** ~$0.01 per interaction vs $0.20 before optimizations

## Further Optimizations (If Needed)

### Prompt Caching (50% cost reduction)
Cache system prompt + tool definitions:
- First call: $0.01
- Subsequent calls: $0.005
- **Annual cost: $2.50** (50% reduction)

### Reduce Tool Definitions
Only send relevant tools per conversation state:
- Current: 20+ tools = ~2,000 tokens
- Optimized: 3-5 tools = ~500 tokens
- **Save: ~$0.002 per call**

### Smart Model Routing
- Haiku: 90% of work (simple tasks)
- Sonnet: 10% of work (complex reasoning only)
- **Target: $0.005 per interaction**

## Bottom Line

**With current optimizations:**
- Most families: $5-10/year
- No subscriptions
- No recurring fees
- Full data ownership
- Self-hosted

**vs typical meal planning subscriptions: $50-60/year**

**Savings: ~$40-50/year** ✨
