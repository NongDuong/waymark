import uuid
from app.database import SessionLocal
from app import models, schemas
from app.api.chat import create_conversation

def run_test():
    db = SessionLocal()
    try:
        print("Starting direct conversation deduplication test...")
        
        # 1. Create or get two test users
        u1_username = "test_user_alpha"
        u2_username = "test_user_beta"
        
        user1 = db.query(models.User).filter_by(username=u1_username).first()
        if not user1:
            user1 = models.User(
                id=uuid.uuid4(),
                username=u1_username,
                primary_email="alpha@test.com",
                hashed_password="hashed_password",
                status=1
            )
            db.add(user1)
            
        user2 = db.query(models.User).filter_by(username=u2_username).first()
        if not user2:
            user2 = models.User(
                id=uuid.uuid4(),
                username=u2_username,
                primary_email="beta@test.com",
                hashed_password="hashed_password",
                status=1
            )
            db.add(user2)
            
        db.commit()
        db.refresh(user1)
        db.refresh(user2)
        
        print(f"Test users ready: User 1: {user1.id}, User 2: {user2.id}")
        
        # 2. Clean up any existing conversations between them
        existing_participants = db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.user_id.in_([user1.id, user2.id])
        ).all()
        
        conv_ids_to_clean = {p.conversation_id for p in existing_participants}
        if conv_ids_to_clean:
            db.query(models.ConversationParticipant).filter(
                models.ConversationParticipant.conversation_id.in_(list(conv_ids_to_clean))
            ).delete(synchronize_session=False)
            db.query(models.Conversation).filter(
                models.Conversation.id.in_(list(conv_ids_to_clean))
            ).delete(synchronize_session=False)
            db.commit()
            print(f"Cleaned up {len(conv_ids_to_clean)} old test conversations.")

        # 3. Create conversation the first time using the endpoint logic
        conv_in = schemas.ConversationCreate(
            participant_user_ids=[user2.id],
            title="Chat 1-1"
        )
        
        print("\n--- Creating conversation for the first time ---")
        import asyncio
        loop = asyncio.get_event_loop()
        res1 = loop.run_until_complete(create_conversation(conv_in=conv_in, db=db, current_user=user1))
        
        print(f"Result 1: ID = {res1.id}, is_existing = {res1.is_existing}")
        assert res1.is_existing is False, "First creation should have is_existing = False"
        
        # 4. Try to create the conversation again
        print("\n--- Trying to create the same conversation again ---")
        res2 = loop.run_until_complete(create_conversation(conv_in=conv_in, db=db, current_user=user1))
        
        print(f"Result 2: ID = {res2.id}, is_existing = {res2.is_existing}")
        assert res2.is_existing is True, "Second creation should have is_existing = True"
        assert res1.id == res2.id, "Conversation IDs must match"
        
        # 5. Let's try from the other user's perspective (User 2 creates to User 1)
        print("\n--- Trying to create from User 2's perspective ---")
        conv_in_reverse = schemas.ConversationCreate(
            participant_user_ids=[user1.id],
            title="Chat 1-1"
        )
        res3 = loop.run_until_complete(create_conversation(conv_in=conv_in_reverse, db=db, current_user=user2))
        print(f"Result 3 (Reverse): ID = {res3.id}, is_existing = {res3.is_existing}")
        assert res3.is_existing is True, "Reverse creation should also find the existing one and return is_existing = True"
        assert res1.id == res3.id, "Reverse conversation ID must match the original one"
        
        print("\n✅ ALL TESTS PASSED SUCCESSFULLY! Deduplication logic is fully correct.")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
