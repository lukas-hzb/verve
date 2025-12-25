"""
API Routes Blueprint.

This blueprint handles all RESTful API endpoints for the Verve application.
Now with user authentication support.
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from typing import Dict, Any

from app.services import VocabService
from app.utils.exceptions import (
    VerveException,
    VocabSetNotFoundError,
    CardNotFoundError,
    InvalidInputError,
    UnauthorizedAccessError
)


api_bp = Blueprint('api', __name__, url_prefix='/api')


def success_response(data: Any = None, message: str = None) -> Dict:
    """
    Create a standardized success response.
    
    Args:
        data: Response data
        message: Optional success message
        
    Returns:
        Dictionary with success status
    """
    response = {'status': 'success'}
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response['data'] = data
    if message:
        response['message'] = message
    return response


def error_response(message: str, code: int = 400) -> tuple:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        code: HTTP status code
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    return jsonify({
        'status': 'error',
        'message': message
    }), code


@api_bp.route("/set/<string:set_id>")
@api_bp.route("/set/<string:set_id>/due_cards")
@login_required
def get_due_cards(set_id: str):
    """
    Get all cards that are due for review in a vocabulary set.
    
    Args:
        set_id: ID of the vocabulary set (Firestore string ID)
        
    Returns:
        JSON response with cards array
    """
    try:
        due_cards = VocabService.get_due_cards(set_id, current_user.id)
        return jsonify({'cards': due_cards})
    except VocabSetNotFoundError as e:
        return error_response(str(e), 404)
    except UnauthorizedAccessError as e:
        return error_response(str(e), 403)
    except Exception as e:
        current_app.logger.error(f"Error fetching due cards: {e}")
        return error_response("An error occurred while fetching cards", 500)


@api_bp.route("/set/<string:set_id>/next_card")
@login_required
def get_next_card(set_id: str):
    """
    Get the next due card for a vocabulary set.
    
    Args:
        set_id: ID of the vocabulary set
        
    Returns:
        JSON response with the next due card or null
    """
    try:
        due_cards = VocabService.get_due_cards(set_id, current_user.id)
        if not due_cards:
            return jsonify({'card': None})
        return jsonify({'card': due_cards[0]})
    except VocabSetNotFoundError as e:
        return error_response(str(e), 404)
    except UnauthorizedAccessError as e:
        return error_response(str(e), 403)
    except Exception as e:
        current_app.logger.error(f"Error fetching next card: {e}")
        return error_response("An error occurred while fetching the next card", 500)


@api_bp.route("/set/<string:set_id>/all")
@api_bp.route("/set/<string:set_id>/cards")
@login_required
def get_all_cards(set_id: str):
    """
    Get all cards in a vocabulary set.
    
    Args:
        set_id: ID of the vocabulary set (Firestore string ID)
        
    Returns:
        JSON response with cards array
    """
    try:
        all_cards = VocabService.get_all_cards(set_id, current_user.id)
        return jsonify({'cards': all_cards})
    except VocabSetNotFoundError as e:
        return error_response(str(e), 404)
    except UnauthorizedAccessError as e:
        return error_response(str(e), 403)
    except Exception as e:
        current_app.logger.error(f"Error fetching all cards: {e}")
        return error_response("An error occurred while fetching cards", 500)


@api_bp.route("/update_card", methods=["POST"])
@api_bp.route("/set/<string:set_id>/rate", methods=["POST"])
@login_required
def update_card(set_id: str = None):
    """
    Update a card based on user performance.
    
    Expected JSON body:
        {
            "set_id": str (optional if in URL),
            "card_front": str,
            "quality": int (0-5)
        }
        
    Returns:
        JSON response with update status and card information
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response("No JSON data provided", 400)
        
        # Extract and validate required fields (set_id from URL or body)
        if set_id is None:
            set_id = data.get('set_id')
        card_front = data.get('card_front')
        quality = data.get('quality')
        
        if not all([set_id is not None, card_front, quality is not None]):
            return error_response("Missing required fields: set_id, card_front, quality", 400)
        
        # Update card through service
        result = VocabService.update_card_performance(set_id, card_front, quality, current_user.id)
        
        return jsonify(success_response(result))
        
    except (VocabSetNotFoundError, CardNotFoundError) as e:
        return error_response(str(e), 404)
    except UnauthorizedAccessError as e:
        return error_response(str(e), 403)
    except InvalidInputError as e:
        return error_response(str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Error updating card: {e}")
        return error_response("An error occurred while updating the card", 500)


@api_bp.route("/restore_card", methods=["POST"])
@login_required
def restore_card():
    """
    Restore a card to a previous state (undo operation).
    
    Expected JSON body:
        {
            "set_id": str (Firestore ID),
            "card_front": str,
            "level": int,
            "next_review": str (ISO format)
        }
        
    Returns:
        JSON response with restore status
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response("No JSON data provided", 400)
        
        # Extract required fields
        set_id = data.get('set_id')
        card_front = data.get('card_front')
        level = data.get('level')
        next_review = data.get('next_review')
        
        if not all([set_id is not None, card_front, level is not None, next_review]):
            return error_response("Missing required fields: set_id, card_front, level, next_review", 400)
        
        # Restore card through service
        result = VocabService.restore_card(set_id, card_front, level, next_review, current_user.id)
        
        return jsonify(success_response(result))
        
    except (VocabSetNotFoundError, CardNotFoundError) as e:
        return error_response(str(e), 404)
    except UnauthorizedAccessError as e:
        return error_response(str(e), 403)
    except InvalidInputError as e:
        return error_response(str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Error restoring card: {e}")
        return error_response("An error occurred while restoring the card", 500)


@api_bp.route("/stats/<string:set_id>")
@login_required
def get_stats(set_id: str):
    """
    Get statistics for a vocabulary set.
    
    Args:
        set_id: ID of the vocabulary set (Firestore string ID)
        
    Returns:
        JSON object with statistics including:
        - total_cards: Total number of cards
        - level_counts: Distribution of cards across levels
        - due_cards: Number of cards due for review
    """
    try:
        stats = VocabService.get_statistics(set_id, current_user.id)
        return jsonify(stats)
    except VocabSetNotFoundError as e:
        return error_response(str(e), 404)
    except UnauthorizedAccessError as e:
        return error_response(str(e), 403)
    except Exception as e:
        current_app.logger.error(f"Error fetching statistics: {e}")
        return error_response("An error occurred while fetching statistics", 500)


@api_bp.route("/reset_set/<string:set_id>", methods=["POST"])
@login_required
def reset_set(set_id: str):
    """
    Reset all cards in a vocabulary set to level 1.
    
    Args:
        set_id: ID of the vocabulary set (Firestore string ID)
        
    Returns:
        JSON response with reset status
    """
    try:
        result = VocabService.reset_set(set_id, current_user.id)
        return jsonify(success_response(result))
    except VocabSetNotFoundError as e:
        return error_response(str(e), 404)
    except UnauthorizedAccessError as e:
        return error_response(str(e), 403)
    except Exception as e:
        current_app.logger.error(f"Error resetting set: {e}")
        return error_response("An error occurred while resetting the set", 500)


@api_bp.route("/vocab_sets", methods=["POST"])
@login_required
def create_vocab_set():
    """
    Create a new vocabulary set for the current user.
    
    Expected JSON body:
        {
            "name": str
        }
        
    Returns:
        JSON response with created set information
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response("No JSON data provided", 400)
        
        set_name = data.get('name')
        if not set_name:
            return error_response("Missing required field: name", 400)
        
        vocab_set = VocabService.create_user_set(current_user.id, set_name)
        
        return jsonify(success_response({
            'id': vocab_set.id,
            'name': vocab_set.name,
            'message': f'Vocabulary set "{set_name}" created successfully'
        })), 201
        
    except InvalidInputError as e:
        return error_response(str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Error creating vocab set: {e}")
        return error_response("An error occurred while creating the vocabulary set", 500)


@api_bp.route("/vocab_sets/<string:set_id>", methods=["DELETE"])
@login_required
def delete_vocab_set(set_id: str):
    """
    Delete a vocabulary set (only if user owns it).
    
    Args:
        set_id: ID of the vocabulary set (Firestore string ID)
        
    Returns:
        JSON response with deletion status
    """
    try:
        result = VocabService.delete_set(set_id, current_user.id)
        return jsonify(success_response(result))
    except VocabSetNotFoundError as e:
        return error_response(str(e), 404)
    except UnauthorizedAccessError as e:
        return error_response(str(e), 403)
    except Exception as e:
        current_app.logger.error(f"Error deleting vocab set: {e}")
        return error_response("An error occurred while deleting the vocabulary set", 500)


@api_bp.route("/user/profile")
@login_required
def get_user_profile():
    """
    Get current user profile information.
    
    Returns:
        JSON object with user profile data
    """
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'created_at': current_user.created_at.isoformat()
    })


# Error handlers for the API blueprint
@api_bp.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors in API routes."""
    return error_response("Resource not found", 404)


@api_bp.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors in API routes."""
    current_app.logger.error(f"Internal server error: {error}")
    return error_response("Internal server error", 500)
