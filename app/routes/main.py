"""
Main Routes Blueprint.

This blueprint handles the main page routes for the Verve application.
Now with user authentication support.
"""

from random import choice

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user

from app.services import VocabService
from app.services.import_service import ImportService
from app.utils.exceptions import (
    CardNotFoundError,
    InvalidInputError,
    UnauthorizedAccessError,
    VocabSetNotFoundError,
)


main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def index():
    """Render the home page or redirect to login."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    sets = VocabService.get_all_set_names(current_user.id)
    sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
    
    return render_template(
        "index.html",
        sets=sets,
        welcome_scene=choice(('sunlit-library', 'warm-desk', 'garden-window')),
        sidebar_collapsed=sidebar_collapsed,
        current_user=current_user
    )


@main_bp.route("/import", methods=["GET", "POST"])
@login_required
def import_set():
    """Handle vocabulary set import."""
    if request.method == "POST":
        try:
            set_name = request.form.get("set_name")
            import_type = request.form.get("import_type", "file")
            
            # Get separators
            card_separator = request.form.get("card_separator", "\\n")
            field_separator = request.form.get("field_separator", "\\t")
            
            # Handle custom separators
            if card_separator == "custom":
                card_separator = request.form.get("custom_card_separator", "\\n")
            if field_separator == "custom":
                field_separator = request.form.get("custom_field_separator", "\\t")
            
            if not set_name:
                flash("Please enter a name for the set.", "error")
                return redirect(url_for('main.import_set'))
            
            file = None
            text_content = None
            
            if import_type == "file":
                file = request.files.get("file")
                if not file or not file.filename:
                    flash("Please select a file.", "error")
                    return redirect(url_for('main.import_set'))
            else:
                text_content = request.form.get("text_content")
                if not text_content:
                    flash("Please enter vocabulary.", "error")
                    return redirect(url_for('main.import_set'))
                
            ImportService.import_set(
                current_user.id, 
                set_name, 
                file=file, 
                text_content=text_content,
                card_separator=card_separator,
                field_separator=field_separator
            )
            
            flash(f"Set '{set_name}' imported successfully!", "success")
            return redirect(url_for("main.index"))
            
        except InvalidInputError:
            flash("The operation could not be completed. Check your input and access permissions.", "error")
            return redirect(url_for('main.import_set'))
        except Exception:
            current_app.logger.exception('Vocabulary set import failed')
            flash("The import failed. Please try again.", "error")
            return redirect(url_for('main.import_set'))
            
    sets = VocabService.get_all_set_names(current_user.id)
    sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
    
    return render_template(
        "import.html",
        sets=sets,
        sidebar_collapsed=sidebar_collapsed,
        current_user=current_user
    )


@main_bp.route("/set/<string:set_id>")
@login_required
def learn_set(set_id: str):
    """
    Render the learning page for a vocabulary set.
    
    Args:
        set_id: ID of the vocabulary set
    """
    try:
        vocab_set = VocabService.get_vocab_set(set_id, current_user.id)
        sets = VocabService.get_all_set_names(current_user.id)
        sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
        
        study_mode = request.args.get('mode', 'learn')
        if study_mode not in ('learn', 'practice', 'mistakes'):
            study_mode = 'learn'

        return render_template(
            "set.html",
            set_id=set_id,
            set_name=vocab_set.name,
            study_mode=study_mode,
            sets=sets,
            sidebar_collapsed=sidebar_collapsed,
            current_user=current_user
        )
    except (VocabSetNotFoundError, UnauthorizedAccessError):
        return redirect(url_for('main.index'))


@main_bp.route("/stats/<string:set_id>")
@login_required
def stats(set_id: str):
    """
    Render the statistics page for a vocabulary set.
    
    Args:
        set_id: ID of the vocabulary set
    """
    try:
        vocab_set = VocabService.get_vocab_set(set_id, current_user.id)
        sets = VocabService.get_all_set_names(current_user.id)
        sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
        
        return render_template(
            "stats.html",
            set_id=set_id,
            set_name=vocab_set.name,
            sets=sets,
            sidebar_collapsed=sidebar_collapsed,
            current_user=current_user
        )
    except (VocabSetNotFoundError, UnauthorizedAccessError):
        return redirect(url_for('main.index'))


@main_bp.route("/set/<string:set_id>/overview")
@login_required
def set_overview(set_id: str):
    """Render the overview page for a vocabulary set.

    Args:
        set_id: ID of the vocabulary set
    """
    try:
        vocab_set = VocabService.get_vocab_set(set_id, current_user.id)
        sets = VocabService.get_all_set_names(current_user.id)
        set_summary = next((item for item in sets if item['id'] == set_id), None)
        if set_summary is not None:
            dominant_level = set_summary['max_level']
        else:
            # Shared sets may not be present in the user's sidebar summaries.
            level_counts = vocab_set.get_statistics()['level_counts']
            display_counts = {}
            for level, count in level_counts.items():
                display_level = max(1, min(level, 5))
                display_counts[display_level] = display_counts.get(display_level, 0) + count
            dominant_level = max(display_counts, key=display_counts.get) if display_counts else 1
        sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
        return render_template(
            "set_overview.html",
            set_id=set_id,
            set_name=vocab_set.name,
            dominant_level=max(1, min(dominant_level, 5)),
            sets=sets,
            sidebar_collapsed=sidebar_collapsed,
            current_user=current_user,
        )
    except (VocabSetNotFoundError, UnauthorizedAccessError):
        return redirect(url_for('main.index'))

# Re-add the original add_card route
@main_bp.route("/set/<string:set_id>/add_card", methods=["POST"])
@login_required
def add_card(set_id: str):
    """Add a new card to a vocabulary set."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        front = data.get("front")
        back = data.get("back")
        
        if not front or not back:
            return jsonify({"error": "Front and back are required"}), 400
            
        card = VocabService.add_card(set_id, front, back, current_user.id)
        
        return jsonify({
            "message": "Card added successfully",
            "card": card.to_dict()
        })
    except InvalidInputError:
        return jsonify({"error": "Invalid card data"}), 400
    except (VocabSetNotFoundError, CardNotFoundError):
        return jsonify({"error": "Card or vocabulary set not found"}), 404
    except UnauthorizedAccessError:
        return jsonify({"error": "Access denied"}), 403
    except Exception:
        current_app.logger.exception('Adding a card failed')
        return jsonify({"error": "Adding the card failed"}), 500

@main_bp.route("/set/<string:set_id>/delete", methods=["POST"])
@login_required
def delete_set(set_id: str):
    """Delete a vocabulary set."""
    try:
        VocabService.delete_set(set_id, current_user.id)
        flash("Set successfully deleted.", "success")
        return redirect(url_for('main.index'))
    except (VocabSetNotFoundError, UnauthorizedAccessError):
        flash("The operation could not be completed. Check your input and access permissions.", "error")
        return redirect(url_for('main.index'))
    except Exception:
        current_app.logger.exception('Deleting a vocabulary set failed')
        flash("Deleting the set failed. Please try again.", "error")
        return redirect(url_for('main.set_overview', set_id=set_id))


@main_bp.route("/set/<string:set_id>/rename", methods=["POST"])
@login_required
def rename_set(set_id: str):
    """Rename a vocabulary set."""
    try:
        new_name = request.form.get("new_name")
        if not new_name:
            flash("Please enter a name.", "error")
            return redirect(url_for('main.set_overview', set_id=set_id))
            
        VocabService.rename_set(set_id, new_name, current_user.id)
        flash("Set renamed successfully!", "success")
        return redirect(url_for('main.set_overview', set_id=set_id))
    except (InvalidInputError, VocabSetNotFoundError, UnauthorizedAccessError):
        flash("The operation could not be completed. Check your input and access permissions.", "error")
        return redirect(url_for('main.set_overview', set_id=set_id))
    except Exception:
        current_app.logger.exception('Renaming a vocabulary set failed')
        flash("Renaming the set failed. Please try again.", "error")
        return redirect(url_for('main.set_overview', set_id=set_id))


@main_bp.route("/set/<string:set_id>/import", methods=["POST"])
@login_required
def import_into_set(set_id: str):
    """Import cards into an existing set."""
    try:
        import_type = request.form.get("import_type", "file")
        
        # Get separators
        card_separator = request.form.get("card_separator", "\\n")
        field_separator = request.form.get("field_separator", "\\t")
        
        # Handle custom separators
        if card_separator == "custom":
            card_separator = request.form.get("custom_card_separator", "\\n")
        if field_separator == "custom":
            field_separator = request.form.get("custom_field_separator", "\\t")
            
        file = None
        text_content = None
        
        if import_type == "file":
            file = request.files.get("file")
            if not file or not file.filename:
                flash("Please select a file.", "error")
                return redirect(url_for('main.set_overview', set_id=set_id))
        else:
            text_content = request.form.get("text_content")
            if not text_content:
                flash("Please enter vocabulary.", "error")
                return redirect(url_for('main.set_overview', set_id=set_id))
            
        count = ImportService.import_into_set(
            current_user.id, 
            set_id, 
            file=file, 
            text_content=text_content,
            card_separator=card_separator,
            field_separator=field_separator
        )
        
        flash(f"{count} cards imported successfully!", "success")
        return redirect(url_for('main.set_overview', set_id=set_id))
    except (InvalidInputError, VocabSetNotFoundError, UnauthorizedAccessError):
        flash("The operation could not be completed. Check your input and access permissions.", "error")
        return redirect(url_for('main.set_overview', set_id=set_id))
    except Exception:
        current_app.logger.exception('Import into vocabulary set failed')
        flash("The import failed. Please try again.", "error")
        return redirect(url_for('main.set_overview', set_id=set_id))


@main_bp.route("/api/set/<string:set_id>/card/<string:card_id>", methods=["PATCH"])
@login_required
def edit_card(set_id: str, card_id: str):
    """Edit both card sides without changing its learning progress."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body required"}), 400
    try:
        card = VocabService.edit_card(set_id, card_id, data.get('front'), data.get('back'), current_user.id)
        return jsonify({"card": card.to_dict()})
    except InvalidInputError as exc:
        return jsonify({"error": str(exc)}), 400
    except (VocabSetNotFoundError, CardNotFoundError):
        return jsonify({"error": "Card or vocabulary set not found"}), 404
    except UnauthorizedAccessError:
        return jsonify({"error": "Access denied"}), 403
    except Exception:
        current_app.logger.exception('Editing a card failed')
        return jsonify({"error": "Saving the card failed. Please try again."}), 500


@main_bp.route("/api/set/<string:set_id>/card/<string:card_id>", methods=["DELETE"])
@login_required
def delete_card(set_id: str, card_id: str):
    """Delete a card from a set."""
    try:
        VocabService.delete_card(set_id, card_id, current_user.id)
        return jsonify({"message": "Card deleted successfully"})
    except (VocabSetNotFoundError, CardNotFoundError):
        return jsonify({"error": "Card or vocabulary set not found"}), 404
    except UnauthorizedAccessError:
        return jsonify({"error": "Access denied"}), 403
    except Exception:
        current_app.logger.exception('Deleting a card failed')
        return jsonify({"error": "Deleting the card failed"}), 500
