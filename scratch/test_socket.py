import asyncio
import uuid
import json
import websockets
import requests
from app.database import SessionLocal
from app import models, schemas
from app.core.security import create_access_token

async def test_websocket_flow():
    db = SessionLocal()
    try:
        print("Starting real-time WebSocket test...")
        
        # 1. Get or create two test users
        u1_username = "test_user_alpha"
        u2_username = "test_user_beta"
        
        user1 = db.query(models.User).filter_by(username=u1_username).first()
        user2 = db.query(models.User).filter_by(username=u2_username).first()
        
        if not user1 or not user2:
            print("Please run scratch/test_conversation.py first to initialize users!")
            return
            
        print(f"Users found: {user1.username} ({user1.id}), {user2.username} ({user2.id})")
        
        # 2. Get the direct conversation between them
        # Let's get the existing conversation directly from the db
        other_user_id = user2.id
        existing_conv = db.query(models.Conversation).join(
            models.ConversationParticipant,
            models.Conversation.id == models.ConversationParticipant.conversation_id
        ).filter(
            models.Conversation.conversation_type == 1,
            models.ConversationParticipant.user_id == user1.id
        ).filter(
            models.Conversation.id.in_(
                db.query(models.ConversationParticipant.conversation_id).filter(
                    models.ConversationParticipant.user_id == other_user_id
                )
            )
        ).first()
        
        if not existing_conv:
            print("Please run scratch/test_conversation.py first to create the conversation!")
            return
            
        conversation_id = existing_conv.id
        print(f"Direct conversation ID: {conversation_id}")
        
        # 3. Generate access tokens
        token1 = create_access_token(data={"sub": str(user1.id)})
        token2 = create_access_token(data={"sub": str(user2.id)})
        print(f"Access Token for User 1 (Alpha): {token1[:20]}...")
        print(f"Access Token for User 2 (Beta): {token2[:20]}...")
        
        # 4. Connect User 1 to the WebSocket endpoint
        ws_url = f"ws://localhost:8000/v1/conversations/ws/{token1}"
        print(f"Connecting to WebSocket: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            print("Connected successfully to WebSocket!")
            
            # Start an async task to send a message as User 2 (Beta) via HTTP POST after 1.5 seconds
            def send_msg_via_http():
                print("\n--- Sending message from User 2 (Beta) via HTTP POST ---")
                headers = {"Authorization": f"Bearer {token2}"}
                url = f"http://localhost:8000/v1/conversations/{conversation_id}/messages"
                payload = {
                    "text_content": "Hello Alpha, this is Beta! Testing WebSocket broadcast.",
                    "media_id": None,
                    "reply_to_message_id": None
                }
                res = requests.post(url, json=payload, headers=headers)
                print(f"HTTP Response Code: {res.status_code}")
                if res.status_code == 200:
                    print(f"HTTP Response Body: {res.json()['id']}")
                else:
                    print(f"HTTP Error: {res.text}")
            
            # Run the HTTP call in an executor since requests is synchronous
            loop = asyncio.get_running_loop()
            await asyncio.sleep(1.0)
            loop.run_in_executor(None, send_msg_via_http)
            
            # 5. Listen for incoming messages on WebSocket
            print("Listening for incoming messages on WebSocket...")
            raw_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print("\nReceived message on WebSocket! Decoding...")
            
            payload = json.loads(raw_response)
            print("Decoded Payload:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            
            # Assert correctness
            assert payload["type"] == "new_message", "Payload type must be 'new_message'"
            assert payload["conversation_id"] == str(conversation_id), "Conversation ID must match"
            assert payload["message"]["text_content"] == "Hello Alpha, this is Beta! Testing WebSocket broadcast.", "Text content must match"
            assert payload["message"]["sender_user_id"] == str(user2.id), "Sender must be User 2"
            
            print("\n✅ WEBSOCKET TEST PASSED SUCCESSFULLY! Real-time sync and cross-worker broadcast is fully working.")
            
    except Exception as e:
        print(f"❌ WEBSOCKET TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_websocket_flow())
