# Vasudeva - Wisdom Guidance System 🕉️

**Ancient Wisdom for Modern Problems**

Vasudeva is a compassionate AI-powered web application that helps people find solutions to their problems using wisdom from sacred texts and great books. Built with RAG (Retrieval-Augmented Generation) technology, it retrieves relevant wisdom passages and provides personalized guidance with empathy and understanding.

---

## ✨ Features

- 🎯 **Problem-Focused Guidance**: Get personalized advice for your specific situation
- 📚 **Sacred Text Retrieval**: Answers backed by ancient wisdom literature
- 💝 **Mental Wellness Support**: Compassionate support for emotional challenges
- 🌐 **Beautiful Responsive UI**: Modern, peaceful interface with smooth animations
- ⚡ **Fast & Intelligent**: Powered by OpenAI GPT-4 and vector search
- 🔒 **Privacy-Focused**: Your problems and conversations stay private

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend (React)                    │
│  - Modern responsive UI with Tailwind CSS                │
│  - Framer Motion animations                              │
│  - Real-time guidance display                            │
└──────────────────┬──────────────────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────────────────┐
│                   Backend (FastAPI)                      │
│  - /api/guidance - Get wisdom guidance                   │
│  - /api/wellness - Mental wellness support               │
│  - /api/search - Search wisdom texts                     │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                Vasudeva RAG Pipeline                     │
│  - Document loading (PDFs)                               │
│  - Text chunking (800 chars with overlap)                │
│  - OpenAI embeddings                                     │
│  - ChromaDB vector store                                 │
│  - GPT-4 for guidance generation                         │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

- Python 3.8+
- Node.js 18+
- OpenAI API key
- PDF documents (sacred texts, wisdom literature) in `documents/` folder

---

## 🚀 Quick Start

### 1️⃣ Clone and Setup

```bash
cd vasudeva
```

### 2️⃣ Setup Backend

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### 3️⃣ Add Your Wisdom Texts

Place your PDF files (Bhagavad Gita, Buddhist texts, philosophical works, etc.) in the `documents/` folder:

```bash
# From project root
ls documents/
# Should show: source2.pdf, ttd.pdf, etc.
```

### 4️⃣ Start Backend Server

```bash
# From backend directory
python api.py
```

The server will:
- Load and process your PDF documents
- Create vector embeddings
- Store in ChromaDB
- Start API server on http://localhost:8000

### 5️⃣ Setup & Start Frontend

In a new terminal:

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: **http://localhost:3000**

---

## 🎮 Usage

### Web Interface

1. Open http://localhost:3000
2. Type your problem or question in the text area
3. Click "Ask Vasudeva"
4. Receive wisdom-based guidance with source citations
5. Expand "View Sacred Wisdom Sources" to see the original text passages

### API Endpoints

#### Get Guidance
```bash
curl -X POST http://localhost:8000/api/guidance \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "I feel anxious about my future",
    "include_sources": true
  }'
```

#### Mental Wellness Support
```bash
curl -X POST http://localhost:8000/api/wellness \
  -H "Content-Type: application/json" \
  -d '{
    "emotion": "anxious",
    "situation": "Worried about career decisions"
  }'
```

#### Search Wisdom
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how to find peace",
    "k": 3
  }'
```

#### Health Check
```bash
curl http://localhost:8000/health
```

---

## 📁 Project Structure

```
vasudeva/
├── documents/                  # Your wisdom texts (PDFs)
│   ├── source2.pdf
│   └── ttd.pdf
│
├── backend/                    # FastAPI backend
│   ├── api.py                 # API endpoints
│   ├── vasudeva_rag.py        # RAG pipeline
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── App.jsx           # Main component
│   │   ├── api.js            # API client
│   │   ├── main.jsx          # Entry point
│   │   └── index.css         # Global styles
│   ├── package.json          # Node dependencies
│   ├── vite.config.js        # Vite configuration
│   ├── tailwind.config.js    # Tailwind CSS config
│   └── index.html            # HTML template
│
├── vectordb/                   # Vector database (auto-generated)
├── README.md                   # This file
└── .gitignore                 # Git ignore rules
```

---

## 🎨 Customization

### Modify RAG Behavior

Edit `backend/vasudeva_rag.py`:

```python
# Change chunk size for different granularity
vasudeva = VasudevaRAG(
    chunk_size=800,      # Smaller = more precise
    chunk_overlap=150,   # More overlap = better context
)

# Change number of retrieved passages
vasudeva.setup_qa_chain(retrieval_k=5)  # Default: 5

# Customize the wisdom prompt
# Edit the wisdom_prompt_template in setup_qa_chain()
```

### Customize UI Theme

Edit `frontend/tailwind.config.js` to change colors:

```javascript
colors: {
  wisdom: {
    light: '#your-color',
    DEFAULT: '#your-color',
    dark: '#your-color',
  }
}
```

### Add More Document Formats

The system currently supports PDFs. To add more formats, modify `vasudeva_rag.py`:

```python
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,      # For .txt files
    Docx2txtLoader,  # For .docx files
)
```

---

## 🔧 Configuration

### Backend Environment Variables

Create `backend/.env`:

```bash
OPENAI_API_KEY=sk-...           # Required
OPENAI_MODEL=gpt-4o-mini        # Optional, default: gpt-4o-mini
CHUNK_SIZE=800                  # Optional, default: 800
CHUNK_OVERLAP=150               # Optional, default: 150
```

### Frontend Environment Variables

Create `frontend/.env`:

```bash
VITE_API_URL=http://localhost:8000  # Backend URL
```

---

## 📊 API Response Examples

### Guidance Response

```json
{
  "problem": "I feel anxious about my future",
  "guidance": "Your anxiety about the future is natural, but remember the wisdom of the Bhagavad Gita: focus on your present actions rather than worrying about outcomes. Do your duty with full effort, but release attachment to results. Peace comes from accepting what you cannot control while diligently working on what you can.",
  "sources": [
    {
      "text": "You have the right to work, but never to the fruit of work...",
      "metadata": {
        "source": "bhagavad-gita.pdf",
        "page": 12
      },
      "relevance_rank": 1
    }
  ],
  "timestamp": "2024-01-15T10:30:00",
  "model": "gpt-4o-mini"
}
```

---

## 🛠️ Troubleshooting

### Backend won't start

```bash
# Check if all dependencies are installed
pip install -r requirements.txt

# Check if .env file exists with valid API key
cat backend/.env

# Check if documents folder has PDFs
ls documents/
```

### Frontend shows "Offline"

```bash
# Make sure backend is running
curl http://localhost:8000/health

# Check if ports are correct in frontend/.env
cat frontend/.env
```

### Poor quality responses

```bash
# Try using GPT-4 instead of GPT-4o-mini
# Edit backend/vasudeva_rag.py:
model_name="gpt-4"

# Increase number of retrieved passages
retrieval_k=7  # Default is 5
```

### Vector DB issues

```bash
# Delete and rebuild vector database
rm -rf vectordb/
python backend/api.py  # Will rebuild on startup
```

---

## 🚢 Deployment

### Deploy Backend (Railway/Render)

1. Create `Procfile`:
```
web: cd backend && uvicorn api:app --host 0.0.0.0 --port $PORT
```

2. Set environment variables in your hosting platform
3. Deploy from Git repository

### Deploy Frontend (Vercel/Netlify)

1. Build command: `cd frontend && npm run build`
2. Output directory: `frontend/dist`
3. Set `VITE_API_URL` to your backend URL

---

## 🤝 Contributing

Contributions are welcome! Some ideas:

- Add support for more document formats (DOCX, TXT, EPUB)
- Implement conversation history and context
- Add voice input/output
- Create mobile app version
- Add support for multiple languages
- Implement user authentication and saved conversations

---

## 📜 License

MIT License - feel free to use for personal or commercial projects.

---

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com)
- Powered by [OpenAI GPT-4](https://openai.com)
- UI built with [React](https://react.dev) and [Tailwind CSS](https://tailwindcss.com)
- Vector storage by [ChromaDB](https://www.trychroma.com)

---

## 📞 Support

Having issues? Check:
1. Backend logs: Check terminal where `api.py` is running
2. Frontend console: Open browser DevTools (F12)
3. API health: Visit http://localhost:8000/health

---

**May wisdom guide your path** 🕉️

Built with ❤️ for seekers of truth and peace
