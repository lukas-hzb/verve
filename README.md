# Verve - Vocabulary Learning App

A modern, Flask-based spaced repetition system for efficient vocabulary learning. Verve uses the SM2 (SuperMemo 2) algorithm to optimize your study sessions by showing cards at scientifically calculated intervals.

## Features

- **Spaced Repetition System**: Uses the proven SM2 algorithm to optimize learning
- **Multiple Vocabulary Sets**: Organize your vocabulary into different sets
- **Practice Mode**: Review all cards in random order without affecting progress
- **Progress Tracking**: Visual statistics showing your learning progress
- **Keyboard Shortcuts**: Efficient navigation with keyboard controls
- **Modern UI**: Clean, responsive design with collapsible sidebar
- **Undo Functionality**: Revert accidental card ratings with the "Back" button
- **Profile Management**: Secure account deletion and data management
- **Card Shuffling**: Randomize card order for varied practice

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone or download the repository**:
   ```bash
   cd /path/to/verve
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python run.py
   ```

5. **Open your browser** and navigate to:
   ```
   http://127.0.0.1:8080
   ```

> **Note**: The application runs on port 8080 to avoid conflicts with macOS services (AirPlay uses port 5000). You can change the port by setting the `FLASK_PORT` environment variable.

## Usage

### Creating Vocabulary Sets

Vocabulary sets are stored as `.tsv` (tab-separated values) files in the `vocab_sets/` directory.

**File format**:
```
Front Side	Back Side	Level	Next Review Date
Apple	Apfel	1	2023-01-01
Book	Buch	1	2023-01-01
```

- **Front Side**: The word or phrase you want to learn
- **Back Side**: The translation or definition
- **Level**: Learning level (1-5+), starts at 1
- **Next Review Date**: When to review next (YYYY-MM-DD format)

### Learning Cards

1. Select a vocabulary set from the sidebar
2. Click on the set name to start learning
3. Press **Space** or click "Flip Card" to reveal the answer
4. Rate your knowledge:
   - Press **A** or click "Didn't Know" if you didn't know the answer
   - Press **D** or click "Knew It!" if you knew the answer
5. The SM2 algorithm automatically schedules the next review
6. Made a mistake? Click the "Back" button to undo your last rating

### Practice Mode

Toggle **Practice Mode** to:
- Review all cards regardless of due date
- Practice without affecting card scheduling
- Cards are shuffled automatically

### Keyboard Shortcuts

- **Space**: Flip card
- **A**: Mark as "Didn't Know"
- **D**: Mark as "Knew It!"

### Statistics

Click on "Stats" in the sidebar to view:
- Total number of cards
- Distribution across learning levels
- Progress visualization

## Project Structure

```
verve/
├── app/                      # Application package
│   ├── __init__.py          # Application factory
│   ├── models/              # Data models
│   │   └── vocab_set.py     # VocabSet and Card models
│   ├── services/            # Business logic
│   │   ├── vocab_service.py # Vocabulary operations
│   │   └── sm2_algorithm.py # Spaced repetition algorithm
│   ├── routes/              # Flask blueprints
│   │   ├── main.py          # Page routes
│   │   └── api.py           # API endpoints
│   └── utils/               # Utility functions
│       ├── exceptions.py    # Custom exceptions
│       └── validators.py    # Input validation
├── static/                  # Static assets
│   ├── css/
│   │   └── style.css       # Application styles
│   ├── js/
│   │   └── app.js          # Frontend JavaScript
│   └── images/
├── templates/              # Jinja2 templates
│   ├── base.html           # Base template with sidebar
│   ├── index.html          # Home page
│   ├── set.html            # Learning page
│   └── stats.html          # Statistics page
├── vocab_sets/             # Your vocabulary TSV files
├── config.py               # Configuration management
├── run.py                  # Application entry point
└── requirements.txt        # Python dependencies
```

## API Documentation

### Get Due Cards
```
GET /api/set/<set_name>
Returns cards due for review
```

### Get All Cards
```
GET /api/set/<set_name>/all
Returns all cards in the set
```

### Update Card
```
POST /api/update_card
Body: {
  "set_name": "string",
  "card_front": "string",
  "quality": 0-5
}
```

### Restore Card (Undo)
```
POST /api/restore_card
Body: {
  "set_name": "string",
  "card_front": "string",
  "level": number,
  "next_review": "ISO date string"
}
```

### Get Statistics
```
GET /api/stats/<set_name>
Returns statistics for the set
```

### Reset Set
```
POST /api/reset_set/<set_name>
Resets all cards to level 1
```

## Configuration

The application can be configured through environment variables:

- `FLASK_CONFIG`: Configuration mode (`development`, `production`, `testing`)
- `FLASK_HOST`: Host to bind to (default: `127.0.0.1`)
- `FLASK_PORT`: Port to bind to (default: `5000`)
- `SECRET_KEY`: Secret key for session management (required in production)

Example:
```bash
export FLASK_CONFIG=production
export SECRET_KEY=your-secret-key-here
python run.py
```

## The SM2 Algorithm

Verve uses the SM2 (SuperMemo 2) algorithm, which:
- Schedules cards based on how well you know them
- Increases intervals for well-known cards (1 day → 6 days → ~2 weeks → ~1 month...)
- Resets poorly-known cards to start over
- Adapts to your individual learning pace

## Development

### Running in Development Mode

```bash
export FLASK_CONFIG=development
python run.py
```

### Code Quality

The codebase follows Python best practices:
- Type hints for better IDE support and error detection
- Comprehensive docstrings
- Input validation and error handling
- Modular architecture with clear separation of concerns
- RESTful API design

## License

This project is open source and available for personal and educational use.

## Credits

- SM2 Algorithm: [SuperMemo](https://www.supermemo.com/)
- Icons: [Feather Icons](https://feathericons.com/)
- Font: [Google Fonts - Poppins](https://fonts.google.com/specimen/Poppins)

## Support

For issues, questions, or contributions, please refer to the project repository.

---

**Happy Learning! 📚✨**
