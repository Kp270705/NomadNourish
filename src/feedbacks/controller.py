# src/feedback/controller.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from database.core import get_db
# Keep FeedbackCreate, it works for both create and update payload
from models.r_schema import FeedbackCreate, Feedback 
from models.r_model import Feedback as FeedbackModel, Order as OrderModel, User as UserModel
from user.service import get_current_user

router = APIRouter(
    prefix='/feedback',
    tags=['feedback']
)

# Use POST for both creating and updating feedback
@router.post("/", response_model=Feedback) 
def submit_or_update_feedback( # Renamed function for clarity
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    # 1. Verify the order exists and belongs to the user
    db_order = db.query(OrderModel).filter(
        OrderModel.id == feedback_data.order_id,
        OrderModel.user_id == current_user.id
    ).first()

    if not db_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or does not belong to this user."
        )
        
    # --- UPSERT LOGIC ---
    # 2. Check if feedback already exists for this order BY THIS USER
    existing_feedback = db.query(FeedbackModel).filter(
        FeedbackModel.order_id == feedback_data.order_id,
        FeedbackModel.user_id == current_user.id # Important: Ensure user owns the feedback
    ).first()

    if existing_feedback:
        # --- UPDATE PATH ---
        print(f"Updating existing feedback for order {feedback_data.order_id}")
        existing_feedback.comments = feedback_data.comments
        existing_feedback.rating = feedback_data.rating
        db_feedback = existing_feedback # Use the existing object
    else:
        # --- CREATE PATH ---
        print(f"Creating new feedback for order {feedback_data.order_id}")
        db_feedback = FeedbackModel(
            comments=feedback_data.comments,
            rating=feedback_data.rating,
            order_id=feedback_data.order_id,
            user_id=current_user.id,
            restaurant_id=db_order.restaurant_id 
        )
        db.add(db_feedback) # Add the new object to the session

    # 3. Commit changes (either update or insert)
    db.commit()
    db.refresh(db_feedback) # Refresh to get any DB defaults/updates
    
    return db_feedback


@router.get("/order/{order_id}", response_model=Feedback)
def get_feedback_for_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieves existing feedback submitted by the current user for a specific order.
    Returns 404 if no feedback exists or the order doesn't belong to the user.
    """
    # Query for feedback, ensuring it matches the order AND the current user
    db_feedback = db.query(FeedbackModel).join(OrderModel).filter(
        FeedbackModel.order_id == order_id,
        FeedbackModel.user_id == current_user.id,
        OrderModel.user_id == current_user.id # Double-check the order also belongs to the user
    ).first()

    # If no feedback is found, return 404
    if not db_feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found for this order by the current user."
        )
    
    # If found, return the feedback details
    return db_feedback

