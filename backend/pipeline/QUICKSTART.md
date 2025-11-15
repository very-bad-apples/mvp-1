# ScriptGenerator Quick Start Guide

## Setup (5 minutes)

### 1. Get Your Anthropic API Key

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-ant-...`)

### 2. Configure Your Environment

Edit `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
```

### 3. Verify Installation

```bash
cd backend
source venv/bin/activate
python -c "from pipeline.script_generator import create_script_generator; print('✓ Ready!')"
```

## Usage (2 minutes)

### Quick Test

```bash
cd backend/pipeline
python << 'EOF'
from script_generator import create_script_generator

generator = create_script_generator()
script = generator.generate_script(
    product_name="Wireless Headphones",
    style="luxury",
    cta_text="Shop Now"
)

print("\n🎬 Generated Script:")
print(f"Hook: {script['hook']}\n")

for i, scene in enumerate(script['scenes'], 1):
    print(f"Scene {i}: {scene.get('voiceover_text', 'N/A')}")

print(f"\nCTA: {script['cta']}")
EOF
```

### Run Test Suite

```bash
cd backend/pipeline
python test_script_generator.py
```

### Run Demos

```bash
cd backend/pipeline
python script_generator_demo.py
```

## Common Issues

### Issue: "ANTHROPIC_API_KEY not configured"

**Solution**: Make sure you've added your API key to `backend/.env`

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Issue: "Rate limit error"

**Solution**: The module automatically retries. If it persists, wait a few minutes.

### Issue: "Image not found"

**Solution**: Verify the image path is correct and the file exists.

## Next Steps

1. Read full documentation: `SCRIPT_GENERATOR_README.md`
2. See integration examples: `INTEGRATION_EXAMPLE.md`
3. Review implementation: `script_generator.py`

## Support

- Check test suite: `python test_script_generator.py`
- Review demos: `python script_generator_demo.py`
- Read docs: `SCRIPT_GENERATOR_README.md`
