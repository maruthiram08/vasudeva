# Quick Start Guide - Vasudeva 🕉️

Get Vasudeva running in 5 minutes!

## Step 1: Install Dependencies (2 min)

```bash
pip install -r requirements.txt
```

## Step 2: Set Up API Key (1 min)

Create a `.env` file:

```bash
echo "OPENAI_API_KEY=sk-your-actual-openai-key-here" > .env
```

Get your OpenAI API key from: https://platform.openai.com/api-keys

## Step 3: Add Your Wisdom Texts (1 min)

Your PDFs should be in the `documents/` folder:

```
documents/
├── source2.pdf  ✓ Already there
└── ttd.pdf      ✓ Already there
```

You can add more PDFs - just drop them in the `documents/` folder!

## Step 4: Launch the App (1 min)

```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`

## First Time Setup

On the first run, Vasudeva will:
1. Load your PDF documents (2-5 seconds)
2. Create text chunks (1-2 seconds)
3. Generate embeddings (10-30 seconds depending on document size)
4. Save to vector database (2-5 seconds)

**Total first-time setup: ~30-60 seconds**

After the first run, the app starts instantly (using cached database)!

## Try It Out!

Once the app is running:

1. You'll see a beautiful calming interface
2. Type a question like: *"I'm feeling anxious about the future"*
3. Click **"Seek Guidance from Vasudeva"**
4. Receive wisdom-based guidance!

## Example Questions

- "How can I find inner peace?"
- "I feel lost and unsure of my purpose"
- "How do I deal with difficult people?"

## Troubleshooting

**Issue**: "No PDF files found"
- **Fix**: Make sure your PDFs are in the `documents/` folder

**Issue**: "OpenAI API key not found"
- **Fix**: Create `.env` file with `OPENAI_API_KEY=your_key`

**Issue**: Port already in use
- **Fix**: Run `streamlit run app.py --server.port 8502` (or any other port)

## Next Steps

- Read the full [README.md](README.md) for advanced features
- Add more wisdom texts to `documents/` folder
- Customize the UI in `app.py`
- Try the API version with `python api.py`

---

🙏 Enjoy your journey with Vasudeva!

