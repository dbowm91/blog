# Static Assets (`app/static/`)

Frontend JavaScript and CSS assets.

## Directory Structure

```
app/static/
├── js/
│   ├── admin/          # Admin dashboard JS
│   ├── public/         # Public site JS
│   └── shared/         # Shared components
├── css/               # SCSS/CSS files (base.css, layout.css, forms.css, admin.css, public.css, etc.)
├── uploads/            # User-uploaded media
└── dist/               # Vite build output
```

## JavaScript

### Admin JS
- Dashboard functionality
- Post editor enhancements
- Media management
- Settings forms

### Public JS
- Comments submission
- Newsletter subscription
- Search functionality

## CSS

Stylesheets in `app/static/css/`:
- Base styles
- Component styles
- Theme-specific styles

## Vite Configuration

Located at `vite.config.js`:
- JavaScript bundling
- SCSS/CSS processing
- Asset optimization

## See Also
- [Templates](frontend/templates.md) - Jinja2 templates
- [App Factory](core/app-factory.md) - Vite initialization
