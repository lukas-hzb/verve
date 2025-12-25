"""
Main Routes Blueprint.

This blueprint handles the main page routes for the Verve application.
Now with user authentication support.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.services import VocabService
from app.services.import_service import ImportService
from app.utils.exceptions import InvalidInputError


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
                flash("Bitte geben Sie einen Namen für das Set ein.", "error")
                return redirect(request.url)
            
            file = None
            text_content = None
            
            if import_type == "file":
                file = request.files.get("file")
                if not file or not file.filename:
                    flash("Bitte wählen Sie eine Datei aus.", "error")
                    return redirect(request.url)
            else:
                text_content = request.form.get("text_content")
                if not text_content:
                    flash("Bitte geben Sie Vokabeln ein.", "error")
                    return redirect(request.url)
                
            ImportService.import_set(
                current_user.id, 
                set_name, 
                file=file, 
                text_content=text_content,
                card_separator=card_separator,
                field_separator=field_separator
            )
            
            flash(f"Set '{set_name}' erfolgreich importiert!", "success")
            return redirect(url_for("main.index"))
            
        except InvalidInputError as e:
            flash(str(e), "error")
            return redirect(request.url)
        except Exception as e:
            flash(f"Ein Fehler ist aufgetreten: {str(e)}", "error")
            return redirect(request.url)
            
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
        
        return render_template(
            "set.html",
            set_id=set_id,
            set_name=vocab_set.name,
            sets=sets,
            sidebar_collapsed=sidebar_collapsed,
            current_user=current_user
        )
    except Exception as e:
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
    except Exception as e:
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
        sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
        return render_template(
            "set_overview.html",
            set_id=set_id,
            set_name=vocab_set.name,
            sets=sets,
            sidebar_collapsed=sidebar_collapsed,
            current_user=current_user,
        )
    except Exception as e:
        import sys
        import traceback
        sys.stderr.write(f"DEBUG: Error in set_overview: {str(e)}\n")
        traceback.print_exc()
        return redirect(url_for('main.index'))

# Re-add the original add_card route
@main_bp.route("/set/<string:set_id>/add_card", methods=["POST"])
@login_required
def add_card(set_id: str):
    """Add a new card to a vocabulary set."""
    try:
        data = request.get_json()
        front = data.get("front")
        back = data.get("back")
        
        if not front or not back:
            return jsonify({"error": "Front and back are required"}), 400
            
        card = VocabService.add_card(set_id, front, back, current_user.id)
        
        return jsonify({
            "message": "Card added successfully",
            "card": card.to_dict()
        })
    except InvalidInputError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route("/set/<string:set_id>/delete", methods=["POST"])
@login_required
def delete_set(set_id: str):
    """Delete a vocabulary set."""
    try:
        VocabService.delete_set(set_id, current_user.id)
        flash("Set successfully deleted.", "success")
        return redirect(url_for('main.index'))
    except Exception as e:
        flash(f"Error deleting set: {str(e)}", "error")
        return redirect(url_for('main.set_overview', set_id=set_id))


@main_bp.route("/set/<string:set_id>/rename", methods=["POST"])
@login_required
def rename_set(set_id: str):
    """Rename a vocabulary set."""
    try:
        new_name = request.form.get("new_name")
        if not new_name:
            flash("Bitte geben Sie einen Namen ein.", "error")
            return redirect(url_for('main.set_overview', set_id=set_id))
            
        VocabService.rename_set(set_id, new_name, current_user.id)
        flash("Set erfolgreich umbenannt!", "success")
        return redirect(url_for('main.set_overview', set_id=set_id))
    except Exception as e:
        flash(f"Fehler beim Umbenennen: {str(e)}", "error")
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
                flash("Bitte wählen Sie eine Datei aus.", "error")
                return redirect(url_for('main.set_overview', set_id=set_id))
        else:
            text_content = request.form.get("text_content")
            if not text_content:
                flash("Bitte geben Sie Vokabeln ein.", "error")
                return redirect(url_for('main.set_overview', set_id=set_id))
            
        count = ImportService.import_into_set(
            current_user.id, 
            set_id, 
            file=file, 
            text_content=text_content,
            card_separator=card_separator,
            field_separator=field_separator
        )
        
        flash(f"{count} Karten erfolgreich importiert!", "success")
        return redirect(url_for('main.set_overview', set_id=set_id))
    except Exception as e:
        import sys
        import traceback
        sys.stderr.write(f"DEBUG: Error in import_into_set: {str(e)}\n")
        traceback.print_exc()
        flash(f"Fehler beim Importieren: {str(e)}", "error")
        return redirect(url_for('main.set_overview', set_id=set_id))


@main_bp.route("/api/set/<string:set_id>/card/<string:card_id>", methods=["DELETE"])
@login_required
def delete_card(set_id: str, card_id: str):
    """Delete a card from a set."""
    try:
        VocabService.delete_card(set_id, card_id, current_user.id)
        return jsonify({"message": "Card deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
