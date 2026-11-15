# dnd-dossiers
Dossiers de D&D (Homebrewery) y su versión web.

- `dossiers/*.txt`: fuente única de cada dossier (narxira, eclipso, nabi, dieter, ront).
- `img/`: ilustraciones (`.webp` con fade, listas para usar; `.jpg` originales).
- `tools/feather.py`: pasa un `.jpg` a `.webp` con borde difuminado al ancho de página.
- `tools/build_web.py`: genera `web/<nombre>-dossier.html` desde los `.txt`. Se publica junto a las hojas de combate.

## Actualizar un dossier
1. Cambiar el `.txt` (o las imágenes).
2. `python3 tools/build_web.py` → regenera las páginas web.
3. Republicar la web de hojas de combate con los archivos de `web/`.
