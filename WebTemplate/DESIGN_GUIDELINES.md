# WebTemplate Design System

> **Version**: 1.0.0 | **Last Updated**: 2024-12-24

Eine vollständige Referenz für alle Design-Entscheidungen, Tokens und Patterns dieses Systems. Folge diesen Richtlinien für konsistente UI-Entwicklung.

---

## Inhaltsverzeichnis

1. [Design Tokens](#1-design-tokens)
   - [Farben](#11-farben)
   - [Typografie](#12-typografie)
   - [Abstände (Spacing)](#13-abstände-spacing)
   - [Radien](#14-radien)
   - [Schatten](#15-schatten)
   - [Transitions](#16-transitions)
2. [Layouts & Spacing-Regeln](#2-layouts--spacing-regeln)
3. [Cards](#3-cards)
4. [Buttons](#4-buttons)
5. [Formulare & Inputs](#5-formulare--inputs)
6. [Popups / Modals](#6-popups--modals)
7. [Sidebar](#7-sidebar)
8. [Icons](#8-icons)
9. [Neue Elemente hinzufügen](#9-neue-elemente-hinzufügen)
10. [Checkliste für neue Komponenten](#10-checkliste-für-neue-komponenten)

---

## 1. Design Tokens

Alle Werte sind in [variables.css](file:///Users/lukasharzbecker/WebProjects/WebTemplate/static/css/variables.css) definiert. **Verwende immer CSS-Variablen, niemals hardcodierte Werte.**

### 1.1 Farben

| Variable | Wert | Verwendung |
| :--- | :--- | :--- |
| `--color-bg-body` | `hsl(0, 0%, 98%)` | Hintergrund der gesamten Seite |
| `--color-bg-surface` | `hsl(0, 0%, 100%)` | Hintergrund von Cards, Popups, Sidebar |
| `--color-bg-surface-hover` | `hsl(210, 25%, 96%)` | Hover-State von Oberflächen |
| `--color-primary` | `#6c63ff` | Primäre Akzentfarbe |
| `--color-primary-muted` | `hsl(242, 100%, 76%)` | Weichere Version für Buttons, Icons |
| `--color-primary-muted-hover` | `hsl(242, 100%, 73%)` | Hover-State |
| `--color-text-main` | `rgb(20, 23, 31)` | Haupttext, Überschriften |
| `--color-text-muted` | `rgb(92, 97, 107)` | Sekundärer Text, Beschreibungen |
| `--color-border` | `rgb(225, 230, 237)` | Alle Borders |

#### Akzentfarben

| Variable | Farbe | Hex | Typische Verwendung |
| :--- | :--- | :--- | :--- |
| `--color-accent-1` | Rot | `#ff6b6b` | Fehler, Warnung, Danger |
| `--color-accent-2` | Orange | `#ff9f43` | Highlights, Trends |
| `--color-accent-3` | Gelb | `#feca57` | Hinweise, Nachrichten |
| `--color-accent-4` | Grün | `#1dd1a1` | Erfolg, Bestätigung |
| `--color-accent-5` | Blau | `#54a0ff` | Info, Neutral |
| `--color-accent-6` | Violett | `#7d5fff` | Premium, Verifiziert |

> [!TIP]
> Verwende `color-mix(in srgb, var(--color-accent-X) NN%, transparent)` für transparente Varianten.

---

### 1.2 Typografie

| Eigenschaft | Variable | Wert |
| :--- | :--- | :--- |
| **Basis-Schriftart** | `--font-family-base` | `'Inter', system-ui, sans-serif` |
| **Display-Schriftart** | `--font-family-display` | `'Outfit', system-ui, sans-serif` |

#### Schriftgrößen

| Variable | Wert | rem | Verwendung |
| :--- | :--- | :--- | :--- |
| `--font-size-sm` | 0.875rem | 14px | Labels, Metadaten |
| `--font-size-base` | 1rem | 16px | Fließtext |
| `--font-size-lg` | 1.125rem | 18px | Lead-Text |
| `--font-size-xl` | 1.25rem | 20px | Card-Titel, H3 |
| `--font-size-2xl` | 1.5rem | 24px | Section-Titel, H2 |
| `--font-size-3xl` | 2rem | 32px | Page-Titel, H1 |

#### Regeln

- **H1-H6**: Verwenden `--font-family-display` mit `font-weight: 700`.
- **Fließtext**: Verwendet `--font-family-base`.
- **Card-Titel** innerhalb von Cards: Verwenden `.card-normal-title` (setzt automatisch Schrift, Größe, Margin).

---

### 1.3 Abstände (Spacing)

| Variable | rem | px | Verwendung |
| :--- | :--- | :--- | :--- |
| `--space-1` | 0.25rem | 4px | Minimaler Innenabstand |
| `--space-2` | 0.5rem | 8px | Enge Gruppen (Icons + Text) |
| `--space-3` | 0.75rem | 12px | Button-Padding, Gaps |
| `--space-4` | 1rem | 16px | **Standard-Margin nach Überschriften** |
| `--space-6` | 1.5rem | 24px | **Card-Padding, Grid-Gaps** |
| `--space-8` | 2rem | 32px | **Abstand zwischen Sections** |

> [!IMPORTANT]
> **Kritische Konvention**:
> - Sections (Content-Blöcke) haben `margin-bottom: var(--space-8);`
> - H2-Überschriften haben `margin-bottom: var(--space-4);`
> - Cards haben `padding: var(--space-6);`

---

### 1.4 Radien

| Variable | Wert | Verwendung |
| :--- | :--- | :--- |
| `--radius-sm` | 0.375rem (6px) | Kleine Elemente (Badges) |
| `--radius-md` | 0.5rem (8px) | Input-Felder |
| `--radius-lg` | 0.75rem (12px) | Icon-Wrapper |
| `--radius-xl` | 1.5rem (24px) | **Cards, Popups, Sidebar** |
| `--radius-btn` | 1rem (16px) | **Buttons** |
| `--radius-full` | 9999px | Kreise (z.B. Delete-Button) |

---

### 1.5 Schatten

| Variable | Verwendung |
| :--- | :--- |
| `--shadow-sm` | Kleine, subtile Schatten |
| `--shadow-md` | Mittelgroße Elemente |
| `--shadow-lg` | Prominente Elemente |
| `--shadow-card` | **Standard für alle Cards** |
| `--shadow-card-hover` | Hover-State von clickable Cards |

---

### 1.6 Transitions

| Variable | Wert | Verwendung |
| :--- | :--- | :--- |
| `--transition-fast` | 150ms ease | Buttons, kurze Interaktionen |
| `--transition-normal` | 300ms ease | Cards, Popups, größere Animationen |

---

## 2. Layouts & Spacing-Regeln

### Page-Struktur

```html
<div class="home-section">
    <div style="padding: 7px var(--space-6) var(--space-6) var(--space-6); max-width: 1400px; width: 100%; margin: 0 auto;">

        <!-- Section 1 -->
        <div style="margin-bottom: var(--space-8);">
            <h2 style="margin-bottom: var(--space-4);">Section Title</h2>
            <!-- Content hier -->
        </div>

        <!-- Section 2 -->
        <div style="margin-bottom: var(--space-8);">
            ...
        </div>

    </div>
</div>
```

### Regeln

| Regel | Umsetzung |
| :--- | :--- |
| Haupt-Container | `max-width: 1400px`, zentriert |
| Section-Wrapper | `margin-bottom: var(--space-8);` |
| Section-Header (H2) | `margin-bottom: var(--space-4);` |
| Erste Card nach H2 | **Kein** `margin-top` nötig (H2 hat genug Abstand) |
| Abstände zwischen Cards | Via Grid-Gap (`card-grid`) |

---

## 3. Cards

Definiert in [cards.css](file:///Users/lukasharzbecker/WebProjects/WebTemplate/static/css/cards.css).

### Base Styles (Gemeinsame Eigenschaften)

Alle folgenden Klassen teilen diese Basis:

```css
background-color: var(--color-bg-surface);
border: 1px solid var(--color-border);
border-radius: var(--radius-xl);    /* 24px */
padding: var(--space-6);             /* 24px */
box-shadow: var(--shadow-card);
```

| Klasse | Spezifische Eigenschaften |
| :--- | :--- |
| `.card-normal` | Standard-Card |
| `.card-clickable` | Hover-Effekte, Pfeil-Icon rechts |
| `.card-stat` | Flexbox für Icon + Wert |
| `.card-list` | Padding `var(--space-2) 0` (für edge-to-edge Items) |
| `.card-progress` | Enthält Fortschrittsbalken |
| `.card-attention` | Border `2px`, roter Hintergrund/Schatten |
| `.card-header-secondary` | Flexbox: Titel links, Buttons rechts |

### Header Cards

| Klasse | Verwendung |
| :--- | :--- |
| `.card-header` | **Primär**: Großes Banner mit Gradient, für Seitentitel |
| `.card-header-secondary` | **Sekundär**: Surface-Hintergrund, für Unterseiten-Header mit Actions |

### Grids

| Klasse | Spalten | Responsive |
| :--- | :--- | :--- |
| `.card-grid` | Auto-fit, min 300px | Ja |
| `.card-grid-2` | 2 Spalten | 1 bei < 768px |
| `.card-grid-3` | 3 Spalten | 2 bei < 1024px, 1 bei < 768px |

---

## 4. Buttons

Definiert in [buttons.css](file:///Users/lukasharzbecker/WebProjects/WebTemplate/static/css/buttons.css).

### Varianten

| Klasse | Aussehen | Verwendung |
| :--- | :--- | :--- |
| `.btn-primary` | Lila Hintergrund, weiß | Hauptaktion |
| `.btn-secondary` | Weißer Hintergrund, Border | Sekundäre Aktion |
| `.btn-danger` | Roter Hintergrund | Destruktive Aktionen |
| `.btn-danger-secondary` | Roter Rand, transparenter Hintergrund | "Abbrechen" bei Danger-Dialogen |

### Button Groups

```html
<div class="button-group">
    <button class="btn-primary">Speichern</button>
    <button class="btn-secondary">Abbrechen</button>
</div>
```

- Alle Buttons im Group haben **gleiche Breite** (`flex: 1 1 0`).
- Verwende `.button-spacer` bis `.button-spacer-5` um Buttons schmaler zu machen.

### Icons in Buttons

```html
<button class="btn-primary">
    <span class="material-symbols-outlined">save</span>
    Speichern
</button>
```

- Icons werden automatisch mit `gap: var(--space-2)` platziert.

---

## 5. Formulare & Inputs

Definiert in [style.css](file:///Users/lukasharzbecker/WebProjects/WebTemplate/static/css/style.css).

### Klassen

| Klasse | Verwendung |
| :--- | :--- |
| `.card-input-group` | Container für Label + Input + Hint |
| `.card-input` | Text-Input oder Textarea |
| `.card-input-description` | Hilfetext unter dem Input |
| `.card-input-icon` | Material-Icon im Input |
| `.card-input-with-icon` | Input mit linker Icon-Padding |

### Focus-State

Inputs erhalten bei Focus:
- `border-color: var(--color-primary-muted);`
- `box-shadow: 0 0 0 3px var(--color-primary-muted-hover);`

---

## 6. Popups / Modals

Definiert in [popups.css](file:///Users/lukasharzbecker/WebProjects/WebTemplate/static/css/popups.css).

### Struktur

```html
<div class="popup-overlay" id="myPopup">
    <div class="popup-content">
        <div class="popup-header">
            <h3 class="popup-title">Titel</h3>
            <button class="popup-close-btn">
                <span class="material-symbols-outlined">close</span>
            </button>
        </div>
        <div class="popup-body">
            <p>Inhalt...</p>
        </div>
        <div class="popup-footer">
            <button class="btn-secondary">Abbrechen</button>
            <button class="btn-primary">Bestätigen</button>
        </div>
    </div>
</div>
```

### Varianten

| Variante | Klasse | Besonderheit |
| :--- | :--- | :--- |
| Standard | `.popup-content` | Weißer Hintergrund |
| Attention | `.popup-content.popup-attention` | Roter Border, kein Close-Button |

### JavaScript

```javascript
openPopup('popupId');   // Zeigt Popup
closePopup('popupId');  // Versteckt Popup
```

---

## 7. Sidebar

Definiert in [sidebar.css](file:///Users/lukasharzbecker/WebProjects/WebTemplate/static/css/sidebar.css).

### Dimensionen

| Variable | Wert |
| :--- | :--- |
| `--sidebar-width` | 260px |
| `--sidebar-width-closed` | 82px |
| `--sidebar-offset` | 15px (Abstand vom Rand) |
| `--sidebar-icon-width` | 60px |

### Zustände

- `.sidebar`: Offen
- `.sidebar.close`: Geschlossen (nur Icons sichtbar)

---

## 8. Icons

### Material Symbols

Wir verwenden [Material Symbols Outlined](https://fonts.google.com/icons?icon.set=Material+Symbols).

```html
<span class="material-symbols-outlined">icon_name</span>
```

### Größen

| Kontext | Größe |
| :--- | :--- |
| In Buttons | 20px (automatisch via CSS) |
| In Cards (Attention, Clickable) | 28px |
| In Icon-Wrappern | 32px |
| In Sidebar | 24px |

---

## 9. Neue Elemente hinzufügen

### Schritt-für-Schritt Anleitung

1. **Prüfe, ob ein bestehendes Pattern passt**
   - Scrolle durch `debug.html` für alle existierenden Komponenten.
   - Kann eine bestehende Klasse erweitert werden?

2. **Definiere Base-Styles**
   - Füge die neue Klasse **zur bestehenden Base-Selector-Liste** hinzu (z.B. in `cards.css` Zeile 5-12).
   - Dadurch erbt sie automatisch: `background`, `border`, `radius`, `padding`, `shadow`.

3. **Definiere spezifische Styles**
   - Schreibe einen eigenen Block für Layout, Typografie, etc.
   - Vermeide das Überschreiben von Base-Eigenschaften (außer bei beabsichtigten Varianten wie `.card-attention`).

4. **Füge zur Typography-Selector-Liste hinzu (falls Titel benötigt)**
   - Base: `cards.css` Zeile 59-70
   - Spezifisch: Schriftgröße definieren

5. **Dokumentiere in `debug.html`**
   - Erstelle eine neue Section mit Beispiel-HTML.

---

## 10. Checkliste für neue Komponenten

Vor dem Commit einer neuen Komponente, prüfe:

- [ ] Verwendet nur CSS-Variablen, keine hardcodierten Werte
- [ ] Erbt Base-Styles wo sinnvoll
- [ ] Padding ist `var(--space-6)` (24px)
- [ ] Border-Radius ist `var(--radius-xl)` (24px)
- [ ] Border ist `1px solid var(--color-border)`
- [ ] Schatten ist `var(--shadow-card)`
- [ ] Transitions verwenden `var(--transition-normal)` oder `var(--transition-fast)`
- [ ] Hover-States sind definiert
- [ ] Responsive Breakpoints sind berücksichtigt (768px, 1024px)
- [ ] Beispiel in `debug.html` hinzugefügt
- [ ] Spacing-Regeln eingehalten (space-8 für Sections, space-4 für Header)

---

> **Fragen?** Überprüfe die Referenz-Implementierung in [debug.html](file:///Users/lukasharzbecker/WebProjects/WebTemplate/templates/debug.html).
