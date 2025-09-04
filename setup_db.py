#!/usr/bin/env python3
"""
Database setup script for Image to Sketch API
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.database.connection import Base
from app.models.user import User
from app.models.sketch import Sketch


async def create_database():
    """Create database tables if they don't exist."""
    print("Creating database tables...")
    
    try:
        # Create async engine
        engine = create_async_engine(settings.database_url)
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        await engine.dispose()
        print("✅ Database tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        sys.exit(1)


async def check_database_connection():
    """Check if we can connect to the database."""
    print("Checking database connection...")
    
    try:
        engine = create_async_engine(settings.database_url)
        
        async with engine.connect() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        
        await engine.dispose()
        print("✅ Database connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up Image to Sketch API Database")
    print(f"Database URL: {settings.database_url}")
    print("-" * 50)
    
    # Check connection first
    if not asyncio.run(check_database_connection()):
        print("\n💡 Make sure PostgreSQL is running and the database exists:")
        print(f"   createdb fast")
        print(f"   # or connect to postgres and CREATE DATABASE fast;")
        sys.exit(1)
    
    # Create tables
    asyncio.run(create_database())
    
    print("\n🎉 Database setup complete!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run migrations: alembic revision --autogenerate -m 'Initial migration'")
    print("3. Apply migrations: alembic upgrade head")
    print("4. Start the server: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
