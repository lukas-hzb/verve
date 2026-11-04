"""Authenticated JSON API for vocabulary and profile operations."""

from functools import wraps
from io import BytesIO
from typing import Any, Callable, Dict

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.services import VocabService
from app.services.export_service import ExportService, ExportSettingsError
from app.utils.exceptions import (
    CardNotFoundError,
    InvalidInputError,
    UnauthorizedAccessError,
    VocabSetNotFoundError,
)


api_bp = Blueprint('api', __name__, url_prefix='/api')


def success_response(data: Any = None, message: str | None = None) -> Dict:
    response = {'status': 'success'}
    if isinstance(data, dict):
        response.update(data)
    elif data is not None:
        response['data'] = data
    if message:
        response['message'] = message
    return response


def error_response(message: str, code: int = 400):
    return jsonify({'status': 'error', 'message': message}), code


def handle_api_errors(view: Callable) -> Callable:
    """Map domain errors to consistent HTTP responses."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except (VocabSetNotFoundError, CardNotFoundError):
            return error_response('Card or Vocabulary Set not found', 404)
        except UnauthorizedAccessError:
            return error_response('Access denied', 403)
        except InvalidInputError:
            return error_response('Invalid Request Data', 400)
        except Exception:
            current_app.logger.exception('Unhandled API Error in %s', view.__name__)
            return error_response('An internal Error occurred', 500)

    return wrapped


def json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise InvalidInputError('request', 'A JSON object is required')
    return data


def require_fields(data: dict, *fields: str) -> None:
    missing = [field for field in fields if data.get(field) is None]
    if missing:
        raise InvalidInputError('request', f"Missing required Fields: {', '.join(missing)}")


@api_bp.route('/set/<string:set_id>')
@api_bp.route('/set/<string:set_id>/due_cards')
@login_required
@handle_api_errors
def get_due_cards(set_id: str):
    return jsonify({'cards': VocabService.get_due_cards(set_id, current_user.id)})


@api_bp.route('/set/<string:set_id>/next_card')
@login_required
@handle_api_errors
def get_next_card(set_id: str):
    cards = VocabService.get_due_cards(set_id, current_user.id)
    return jsonify({'card': cards[0] if cards else None})


@api_bp.route('/set/<string:set_id>/all')
@api_bp.route('/set/<string:set_id>/cards')
@login_required
@handle_api_errors
def get_all_cards(set_id: str):
    wrong_only = request.args.get('wrong_only', 'false').lower() == 'true'
    last_wrong_only = request.args.get('last_wrong_only', 'false').lower() == 'true'
    cards = VocabService.get_all_cards(set_id, current_user.id, wrong_only=wrong_only, last_wrong_only=last_wrong_only)
    return jsonify({'cards': cards})


@api_bp.get('/set/<string:set_id>/export')
@login_required
@handle_api_errors
def export_set(set_id: str):
    vocab_set = VocabService.get_vocab_set(set_id, current_user.id)
    file_format = request.args.get('format', 'verve')
    try:
        content = ExportService.serialize(
            VocabService.get_all_cards(set_id, current_user.id), file_format,
            request.args.get('field_separator'), request.args.get('card_separator', '\\n'),
            set_name=vocab_set.name,
        )
    except ExportSettingsError as error:
        return error_response(str(error), 400)
    response = send_file(
        BytesIO(content.encode('utf-8')),
        mimetype=ExportService.MIME_TYPES[file_format],
        as_attachment=True,
        download_name=f'{secure_filename(vocab_set.name) or "cards"}.{file_format}',
        max_age=0,
    )
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@api_bp.route('/update_card', methods=['POST'])
@api_bp.route('/set/<string:set_id>/rate', methods=['POST'])
@login_required
@handle_api_errors
def update_card(set_id: str | None = None):
    data = json_body()
    set_id = set_id or data.get('set_id')
    require_fields({**data, 'set_id': set_id}, 'set_id', 'card_front', 'quality')
    result = VocabService.update_card_performance(
        set_id,
        data['card_front'],
        data['quality'],
        current_user.id,
    )
    return jsonify(success_response(result))


def _mark_practice(set_id: str, *, wrong: bool):
    data = json_body()
    require_fields(data, 'card_front')
    operation = VocabService.mark_practice_wrong if wrong else VocabService.mark_practice_correct
    return jsonify(success_response(operation(set_id, data['card_front'], current_user.id)))


@api_bp.route('/set/<string:set_id>/mark_wrong', methods=['POST'])
@login_required
@handle_api_errors
def mark_wrong(set_id: str):
    return _mark_practice(set_id, wrong=True)


@api_bp.route('/set/<string:set_id>/mark_correct', methods=['POST'])
@login_required
@handle_api_errors
def mark_correct(set_id: str):
    return _mark_practice(set_id, wrong=False)


@api_bp.route('/restore_card', methods=['POST'])
@login_required
@handle_api_errors
def restore_card():
    data = json_body()
    require_fields(data, 'set_id', 'card_front', 'level', 'next_review')
    result = VocabService.restore_card(
        data['set_id'],
        data['card_front'],
        data['level'],
        data['next_review'],
        current_user.id,
        last_answer_wrong=data.get('last_answer_wrong'),
    )
    return jsonify(success_response(result))


@api_bp.route('/stats/<string:set_id>')
@login_required
@handle_api_errors
def get_stats(set_id: str):
    return jsonify(VocabService.get_statistics(set_id, current_user.id))


@api_bp.route('/reset_set/<string:set_id>', methods=['POST'])
@login_required
@handle_api_errors
def reset_set(set_id: str):
    return jsonify(success_response(VocabService.reset_set(set_id, current_user.id)))


@api_bp.route('/vocab_sets', methods=['POST'])
@login_required
@handle_api_errors
def create_vocab_set():
    data = json_body()
    require_fields(data, 'name')
    vocab_set = VocabService.create_user_set(current_user.id, data['name'])
    return jsonify(success_response({
        'id': vocab_set.id,
        'name': vocab_set.name,
        'message': f'Vocabulary Set "{vocab_set.name}" created successfully',
    })), 201


@api_bp.route('/vocab_sets/<string:set_id>', methods=['DELETE'])
@login_required
@handle_api_errors
def delete_vocab_set(set_id: str):
    return jsonify(success_response(VocabService.delete_set(set_id, current_user.id)))


@api_bp.route('/set/<string:set_id>/shuffle', methods=['POST'])
@login_required
@handle_api_errors
def save_shuffle_order(set_id: str):
    data = json_body()
    require_fields(data, 'card_ids')
    result = VocabService.save_shuffle_order(set_id, data['card_ids'], current_user.id)
    return jsonify(success_response(result))


@api_bp.route('/user/profile')
@login_required
def get_user_profile():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'created_at': current_user.created_at.isoformat(),
    })


@api_bp.errorhandler(404)
def api_not_found(_error):
    return error_response('Resource not found', 404)


@api_bp.errorhandler(500)
def api_internal_error(error):
    current_app.logger.error('Internal API Error: %s', error)
    return error_response('Internal Server Error', 500)


@api_bp.route('/folders', methods=['POST'])
@api_bp.route('/folders/<string:folder_id>', methods=['PATCH', 'DELETE'])
@login_required
@handle_api_errors
def manage_folder(folder_id=None):
    from app.services.folder_service import FolderService
    if request.method == 'DELETE':
        FolderService.delete(folder_id, current_user.id)
        return jsonify(success_response())
    data = json_body()
    require_fields(data, 'name')
    folder = FolderService.save(current_user.id, data['name'], folder_id)
    return jsonify(success_response({'id': folder.id, 'name': folder.name})), (201 if request.method == 'POST' else 200)


@api_bp.put('/set/<string:set_id>/folder')
@login_required
@handle_api_errors
def assign_folder(set_id):
    from app.services.folder_service import FolderService
    data = json_body()
    if 'folder_id' not in data or (data['folder_id'] is not None and not isinstance(data['folder_id'], str)):
        raise InvalidInputError('folder_id', 'Folder ID or null required')
    FolderService.assign(data['folder_id'], set_id, current_user.id)
    return jsonify(success_response())


@api_bp.get('/folder/<string:folder_id>/cards')
@api_bp.get('/folder/<string:folder_id>/due_cards')
@login_required
@handle_api_errors
def folder_cards(folder_id):
    from app.services.folder_service import FolderService
    mode = ('learn' if request.path.endswith('/due_cards') else
            'mistakes' if request.args.get('last_wrong_only') == 'true' else 'practice')
    return jsonify({'cards': FolderService.cards(folder_id, current_user.id, mode)})


@api_bp.put('/folders/<string:folder_id>/sets')
@login_required
@handle_api_errors
def replace_folder_sets(folder_id):
    from app.services.folder_service import FolderService
    data = json_body()
    require_fields(data, 'set_ids', 'name')
    FolderService.replace_sets(folder_id, current_user.id, data['set_ids'], data['name'])
    return jsonify(success_response())
