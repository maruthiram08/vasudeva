#!/bin/bash

# Vasudeva Setup Script
# This script helps you set up Vasudeva quickly

echo "🕉️  Welcome to Vasudeva Setup"
echo "================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found: Python $python_version"

# Check if documents folder exists
if [ ! -d "documents" ]; then
    echo "❌ Error: 'documents/' folder not found"
    echo "   Creating documents folder..."
    mkdir documents
    echo "   ✅ Created 'documents/' folder"
    echo "   📚 Please add your wisdom texts (PDFs) to this folder"
else
    pdf_count=$(find documents -name "*.pdf" | wc -l | xargs)
    echo "✅ Found 'documents/' folder with $pdf_count PDF(s)"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "🔑 Setting up API key..."
    echo "   Creating .env file..."
    
    echo "   Please enter your OpenAI API key:"
    echo "   (Get it from: https://platform.openai.com/api-keys)"
    read -p "   API Key: " api_key
    
    if [ -z "$api_key" ]; then
        echo "   ⚠️  No API key entered. Creating template .env file..."
        echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
        echo "   📝 Please edit .env file and add your API key"
    else
        echo "OPENAI_API_KEY=$api_key" > .env
        echo "   ✅ API key saved to .env"
    fi
else
    echo "✅ Found .env file"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
read -p "   Install Python packages now? (y/n): " install_choice

if [ "$install_choice" = "y" ] || [ "$install_choice" = "Y" ]; then
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "   ✅ Dependencies installed successfully"
    else
        echo "   ❌ Error installing dependencies"
        echo "   Try: pip install -r requirements.txt"
    fi
else
    echo "   ⏭️  Skipped. Run manually: pip install -r requirements.txt"
fi

# Final instructions
echo ""
echo "================================"
echo "✨ Setup Complete!"
echo "================================"
echo ""
echo "📚 Next steps:"
echo "   1. Ensure your wisdom texts (PDFs) are in 'documents/' folder"
echo "   2. Verify your API key in .env file"
echo "   3. Run: streamlit run app.py"
echo ""
echo "📖 For detailed instructions, see:"
echo "   - QUICKSTART.md (5-minute guide)"
echo "   - README.md (full documentation)"
echo ""
echo "🙏 May Vasudeva guide you on your journey!"
echo ""

