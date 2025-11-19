## **Architecture: 3 Core Layers**

```
INPUT → CREATIVE BRAIN → PRODUCTION ENGINE → OUTPUT
```

**1. Creative Brain** (LLM orchestration)
- Analyzes product → Generates script → Plans scenes → Directs execution

**2. Production Engine** (Asset generation + assembly)
- Generates/sources visuals → Syncs to script → Assembles timeline

**3. Quality Control** (Validation)
- Checks pacing, text readability, audio sync

---

## **Best Tool Stack**

### **Creative Brain**
- **Script Generation**: Claude 3.5 Sonnet (you're already here - best at creative + following formulas)
- **Structured Output**: Use JSON mode for scene breakdowns
  
### **Voiceover**
- **ElevenLabs** (non-negotiable - most natural, fast)
- Use their "conversational" voices for UGC feel

### **Visuals**
**Start Simple:**
- **Product shots**: User-provided images
- **B-roll**: Pexels API (free, good enough)
- **Text overlays**: Remotion/programmatic (precise control)

**Level Up Later:**
- **Generated video**: Runway Gen-3 or Kling (when you need custom shots)
- Only generate what you can't find in stock

### **Video Assembly**
- **Remotion** (React-based, programmatic control)
  - Frame-perfect timing
  - Easy text animations
  - Version control your templates
- Alternative: **MoviePy** (Python, simpler but less polished)

### **Background Music** (optional for POC)
- Epidemic Sound API or Uppbeat (licensed)
- Keep it subtle, focus on voiceover

---

## **Key Technical Decisions**

### **1. Fixed Template vs. Dynamic Composition?**
**Recommendation**: Start with **3 fixed templates** (Problem-Solution, Testimonial, Feature-Benefit)
- Templates encode proven pacing/structure
- LLM populates content into template slots
- Easier to make consistent bangers

### **2. How Much to Generate vs. Source?**
**Recommendation**: **Source 80%, Generate 20%** for POC
- Source: B-roll, background, generic lifestyle
- Generate: Product-specific scenarios, unique angles
- Reason: Speed + cost + reliability

### **3. Real-time vs. Batch Processing?**
**Recommendation**: **Batch** (render takes 2-3 min, that's fine)
- Focus on quality over speed for POC
- Async pipeline: submit → process → notify
- Can optimize to ~30s later

### **4. Single Video vs. Variants?**
**Recommendation**: **Generate 3 variants per input**
- Different hooks (pain point, benefit, social proof)
- Same product, different angles
- This is your competitive advantage (instant A/B tests)

---

## **Data Flow (Simple)**

```
1. INPUT
   ↓
   Product info + images → Claude

2. CREATIVE BRAIN
   ↓
   Claude generates:
   - Ad script with timing
   - Scene descriptions
   - Text overlay cues
   - B-roll search terms

3. PRODUCTION ENGINE
   ↓
   Parallel execution:
   - ElevenLabs → voiceover.mp3
   - Pexels API → b-roll clips
   - Remotion → text animations
   
4. ASSEMBLY
   ↓
   Remotion composes:
   - Sync voiceover to timeline
   - Place product images at key moments
   - Insert b-roll between shots
   - Add text overlays on beat
   
5. OUTPUT
   ↓
   25-30s video (1080x1920, 30fps, H.264)
```

---

## **What Makes It "Bang"**

### **The LLM Prompt is Everything**
Give Claude:
- 50 examples of winning ad scripts
- Psychological hooks database
- Timing constraints (word count per scene)
- Brand voice rules

### **Pacing Rules** (Hardcode These)
- Scene length: 2-3 seconds MAX
- Text appears: 0.3s before voiceover says it
- Transitions: Quick cuts (0.1s) or swipe (0.2s)
- First 1 second: Text hook + product visible

### **Visual Hierarchy**
1. Product (largest, center)
2. Text overlay (high contrast, readable on mobile)
3. B-roll (supporting context)

---

## **Build Order**

**Week 1**: Script generator + scene planner
- Perfect the script output first
- Test different product inputs
- Nail the timing/pacing logic

**Week 2**: Static template renderer
- Fixed layout, hardcode timing
- Product images + text overlays only
- Prove the assembly works

**Week 3**: Add voiceover + b-roll
- Integrate ElevenLabs
- Pexels API for backgrounds
- Sync to voiceover timing

**Week 4**: Polish + variants
- Smooth transitions
- Generate 3 versions
- Add music (optional)

---

## **Cost Reality Check**

Per video:
- Claude API: $0.10
- ElevenLabs: $0.30 (3,000 characters)
- Runway (if used): $0.50-1.00
- Pexels: Free
- **Total: ~$0.50-1.50 per ad**

Compare to: Agency charges $5K-20K per ad creative.

---

## **The One Thing to Get Right**

**The script generation prompt.** 

If Claude can write scripts that follow proven formulas + match the product + hit psychological triggers → everything else is just execution. Spend 70% of your time perfecting this part.

**Want me to help you write that prompt?**