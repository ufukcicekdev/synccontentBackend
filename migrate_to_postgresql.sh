#!/bin/bash

# SyncContents Database Migration Script
# This script helps migrate from SQLite to PostgreSQL

echo "🚀 SyncContents PostgreSQL Migration Script"
echo "============================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Please activate your virtual environment first:"
    echo "   source venv/bin/activate"
    exit 1
fi

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please update it with your PostgreSQL credentials."
    echo "   DATABASE_URL=postgresql://synccontents_user:your_password@localhost:5432/synccontents_db"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "📦 Installing/updating requirements..."
pip install -r requirements.txt

echo "🔍 Checking database connection..."
python manage.py check --database default

if [[ $? -ne 0 ]]; then
    echo "❌ Database connection failed. Please check your .env configuration."
    exit 1
fi

echo "🗃️  Creating migrations..."
python manage.py makemigrations

echo "📋 Applying migrations..."
python manage.py migrate

echo "👤 Creating superuser (optional)..."
read -p "Do you want to create a superuser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

echo "🧪 Testing database connection..."
python manage.py dbshell -c "\dt"

echo ""
echo "✅ PostgreSQL setup completed successfully!"
echo "🚀 You can now run: python manage.py runserver"