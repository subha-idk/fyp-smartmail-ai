import asyncio
import httpx
from sqlalchemy import select
from app.config import settings
from app.database import async_session_factory
from app.models.user import User

async def main():
    print("Loading settings...")
    print(f"BACKEND_URL: {settings.BACKEND_URL}")
    print(f"API_SECRET_KEY: {settings.API_SECRET_KEY[:4]}***" if settings.API_SECRET_KEY else "API_SECRET_KEY: None")

    # Fetch user ID by email
    email = "patrasuvodip258@gmail.com"
    print(f"Fetching user ID for email '{email}'...")
    async with async_session_factory() as session:
        stmt = select(User).where(User.email == email)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            print(f"Error: User with email '{email}' not found. Please run seed script first.")
            return
        user_id = user.id
        print(f"Found User ID: {user_id}")

    # Set up headers with API secret key
    headers = {
        "X-API-Key": settings.API_SECRET_KEY,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        # First trigger predict to populate ML scores
        print(f"Triggering prediction for user {user_id}...")
        predict_url = f"{settings.BACKEND_URL}/api/predict/{user_id}"
        try:
            predict_res = await client.post(predict_url, headers=headers)
            print(f"Prediction Response ({predict_res.status_code}): {predict_res.text}")
        except Exception as e:
            print(f"Failed to call prediction endpoint: {e}")

        # Now send email
        print(f"Sending email for user {user_id}...")
        send_url = f"{settings.BACKEND_URL}/api/send-email/{user_id}"
        try:
            send_res = await client.post(send_url, headers=headers)
            print(f"Send Email Status Code: {send_res.status_code}")
            if send_res.status_code == 200:
                data = send_res.json()
                print("\n--- API Response Details ---")
                print(f"Status: {data.get('status')}")
                print(f"Email Type: {data.get('email_type')}")
                print(f"Subject: {data.get('subject')}")
                print(f"Tokens Used: {data.get('tokens_used')}")
                print(f"Log ID: {data.get('log_id')}")
            else:
                print(f"Error: {send_res.text}")
        except Exception as e:
            print(f"Failed to call send-email endpoint: {e}")

if __name__ == "__main__":
    asyncio.run(main())
