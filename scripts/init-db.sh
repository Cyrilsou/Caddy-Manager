#!/bin/bash
set -e

echo "=== Caddy Control Panel - Database Initialization ==="

if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set"
    exit 1
fi

echo "Running Alembic migrations..."
cd /app
alembic upgrade head

echo "Creating initial admin user..."
python -c "
import asyncio
from app.database import async_session_factory
from app.models.user import User
from app.security.auth import hash_password
from app.config import settings

async def create_admin():
    async with async_session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
        if result.scalar_one_or_none():
            print(f'Admin user \"{settings.ADMIN_USERNAME}\" already exists, skipping.')
            return
        user = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            is_active=True,
            is_superadmin=True,
        )
        session.add(user)
        await session.commit()
        print(f'Admin user \"{settings.ADMIN_USERNAME}\" created successfully.')

asyncio.run(create_admin())
"

echo "=== Database initialization complete ==="
