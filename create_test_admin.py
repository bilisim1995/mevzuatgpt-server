#!/usr/bin/env python3
"""
Test admin kullanıcısı oluştur
"""
import asyncio
import httpx

API_BASE = "http://localhost:5000"

async def create_admin():
    async with httpx.AsyncClient() as client:
        try:
            # Register
            response = await client.post(
                f"{API_BASE}/api/auth/register",
                json={
                    "email": "testadmin@mevzuatgpt.org",
                    "password": "TestAdmin123!",
                    "confirm_password": "TestAdmin123!",
                    "full_name": "Test Admin",
                    "role": "admin"
                }
            )
            
            print(f"Signup Status: {response.status_code}")
            print(response.text)
            
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(create_admin())
