"""PNG/JPG/JPEG/WebP to DDS converter plug-in for AI Generator."""
from PIL import Image, ImageOps

CONVERTER_INFO = {
    'name': 'PNG / JPG / WebP to DDS',
    'inputs': ('.png', '.jpg', '.jpeg', '.webp'),
    'output': '.dds',
}

FORMATS = {
    'Uncompressed RGBA': None,
    'DXT1 / BC1': 'DXT1',
    'DXT3 / BC2': 'DXT3',
    'DXT5 / BC3': 'DXT5',
    'BC5': 'BC5',
}

def convert_file(source_path, output_path, options=None):
    options = options or {}
    selected = options.get('dds_format', 'Uncompressed RGBA')
    pixel_format = FORMATS.get(selected)
    with Image.open(source_path) as opened:
        image = ImageOps.exif_transpose(opened)
        image.seek(0)
        image = image.convert('RGB' if pixel_format == 'BC5' else 'RGBA')
        save_options = {'format': 'DDS'}
        if pixel_format: save_options['pixel_format'] = pixel_format
        image.save(output_path, **save_options)
